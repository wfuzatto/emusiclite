<?php

require_once __DIR__ . '/MusicExceptions.php';
require_once __DIR__ . '/ComfyCoverService.php';
require_once __DIR__ . '/EbookQueueStatusService.php';

class ResourceGuard
{
    public function __construct(private mysqli $db, private array $config) {}

    public function inspect(): array
    {
        return [
            'free_vram_mb' => $this->freeVramMb(),
            'ebook_processing' => $this->ebookProcessing(),
            'comfy' => (new ComfyCoverService($this->config))->queueStatus(),
        ];
    }

    public function assertHeavyWorkAllowed(bool $needsComfy = false, bool $requiresGpu = true): void
    {
        $state = $this->inspect();
        if ($state['ebook_processing'] > 0) throw new MusicResourceBusyException('Recursos reservados para um trabalho do eBookLite.');
        if ($requiresGpu) {
            if ($state['free_vram_mb'] === null) throw new MusicResourceBusyException('Não foi possível confirmar a memória livre da GPU.');
            if ($state['free_vram_mb'] < $this->config['min_free_vram_mb']) throw new MusicResourceBusyException('Memória de GPU insuficiente; a música continuará pendente.');
        }
        if ($needsComfy) {
            if (empty($state['comfy']['online'])) throw new MusicResourceBusyException('Não foi possível confirmar a fila do ComfyUI.');
            if (($state['comfy']['running'] ?? 0) > 0 || ($state['comfy']['pending'] ?? 0) > 0) throw new MusicResourceBusyException('A fila existente do ComfyUI tem prioridade.');
        }
    }

    public function withHeavySlot(bool $needsComfy, callable $operation, bool $requiresGpu = true)
    {
        $row = $this->db->query("SELECT GET_LOCK('musiclite_heavy_generation',0)")->fetch_row();
        if ((int) ($row[0] ?? 0) !== 1) throw new MusicResourceBusyException('Outra geração musical pesada já está em andamento.');
        try {
            $this->assertHeavyWorkAllowed($needsComfy, $requiresGpu);
            return $operation();
        } finally {
            $this->db->query("SELECT RELEASE_LOCK('musiclite_heavy_generation')");
        }
    }

    public function withTextSlot(callable $operation)
    {
        $row = $this->db->query("SELECT GET_LOCK('musiclite_text_generation',0)")->fetch_row();
        if ((int) ($row[0] ?? 0) !== 1) throw new MusicResourceBusyException('Outro planejamento musical já está em andamento.');
        try {
            if ($this->ebookProcessing() > 0) throw new MusicResourceBusyException('Recursos reservados para um trabalho do eBookLite.');
            return $operation();
        } finally {
            $this->db->query("SELECT RELEASE_LOCK('musiclite_text_generation')");
        }
    }

    private function freeVramMb(): ?int
    {
        $binary = trim((string) shell_exec('command -v nvidia-smi 2>/dev/null'));
        if ($binary === '') return null;
        $lines = []; $code = 0;
        exec(escapeshellarg($binary) . ' --query-gpu=memory.free --format=csv,noheader,nounits 2>/dev/null', $lines, $code);
        if ($code !== 0 || !$lines) return null;
        return min(array_map('intval', $lines));
    }

    private function ebookProcessing(): int
    {
        try { return (new EbookQueueStatusService($this->db, $this->config))->processingCount(); }
        catch (Throwable $e) { throw new MusicResourceBusyException('Não foi possível confirmar a fila do eBookLite.'); }
    }
}
