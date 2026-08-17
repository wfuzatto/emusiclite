<?php

require_once __DIR__ . '/MusicExceptions.php';

class ComfyCoverService
{
    private string $clientId;
    public function __construct(private array $config)
    {
        $this->clientId = 'musiclite-' . bin2hex(random_bytes(12));
    }

    public function healthCheck(): array
    {
        try { $this->request('/system_stats', null, 8, 'GET'); return ['online' => true, 'configured' => $this->config['comfy_workflow'] !== '']; }
        catch (Throwable $e) { return ['online' => false, 'configured' => $this->config['comfy_workflow'] !== '']; }
    }

    public function queueStatus(): array
    {
        try {
            $data = $this->request('/queue', null, 8, 'GET');
            return ['online' => true, 'running' => count($data['queue_running'] ?? []), 'pending' => count($data['queue_pending'] ?? [])];
        } catch (Throwable $e) { return ['online' => false, 'running' => 0, 'pending' => 0]; }
    }

    public function generate(string $prompt, string $destination): array
    {
        $template = $this->config['comfy_workflow'];
        if ($template === '' || !is_readable($template)) throw new MusicPermanentException('Workflow de capa do ComfyUI não foi configurado.');
        $checkpoint = trim((string) ($this->config['comfy_checkpoint'] ?? ''));
        if ($checkpoint === '') throw new MusicPermanentException('Checkpoint de capa do ComfyUI não foi configurado.');
        $raw = file_get_contents($template);
        $workflow = json_decode(str_replace(
            ['{{PROMPT}}','{{CLIENT_ID}}','{{CHECKPOINT}}'],
            [addcslashes($prompt, "\\\"\n\r\t"), $this->clientId, addcslashes($checkpoint, "\\\"")],
            $raw
        ), true);
        if (!is_array($workflow)) throw new MusicPermanentException('Workflow de capa inválido.');
        $response = $this->request('/prompt', ['prompt' => $workflow, 'client_id' => $this->clientId], 30);
        $promptId = (string) ($response['prompt_id'] ?? '');
        if ($promptId === '') throw new MusicTransientException('ComfyUI não aceitou o workflow da capa.');
        $deadline = time() + $this->config['comfy_timeout'];
        $image = null;
        while (time() < $deadline) {
            sleep(3);
            $history = $this->request('/history/' . rawurlencode($promptId), null, 15, 'GET');
            $entry = $history[$promptId] ?? null;
            if (!$entry) continue;
            foreach ($entry['outputs'] ?? [] as $output) {
                foreach ($output['images'] ?? [] as $candidate) { $image = $candidate; break 2; }
            }
            if (!$image) throw new MusicTransientException('ComfyUI finalizou sem produzir uma capa.');
            break;
        }
        if (!$image) throw new MusicTransientException('Tempo limite ao gerar a capa.');
        $query = http_build_query(['filename' => $image['filename'], 'subfolder' => $image['subfolder'] ?? '', 'type' => $image['type'] ?? 'output']);
        $this->download('/view?' . $query, $destination);
        $size = @getimagesize($destination);
        if (!$size || $size[0] < 512 || $size[1] < 512) throw new MusicPermanentException('A capa gerada não possui dimensões válidas.');
        return ['prompt_id' => $promptId, 'path' => $destination, 'width' => $size[0], 'height' => $size[1], 'sha256' => hash_file('sha256', $destination)];
    }

    private function request(string $path, ?array $payload, int $timeout, string $method = 'POST'): array
    {
        $ch = curl_init($this->config['comfy_url'] . $path);
        curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_CONNECTTIMEOUT => 8, CURLOPT_TIMEOUT => $timeout, CURLOPT_CUSTOMREQUEST => $method, CURLOPT_HTTPHEADER => ['Accept: application/json']]);
        if ($payload !== null) { curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES)); curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json','Accept: application/json']); }
        $body = curl_exec($ch); $status = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE); curl_close($ch);
        if ($body === false || $status < 200 || $status >= 300) throw new MusicTransientException('ComfyUI indisponível.');
        $data = json_decode($body, true);
        if (!is_array($data)) throw new MusicTransientException('Resposta inválida do ComfyUI.');
        return $data;
    }

    private function download(string $path, string $destination): void
    {
        $handle = fopen($destination . '.part', 'wb');
        if (!$handle) throw new RuntimeException('Não foi possível criar o arquivo temporário da capa.');
        $ch = curl_init($this->config['comfy_url'] . $path);
        curl_setopt_array($ch, [CURLOPT_FILE => $handle, CURLOPT_CONNECTTIMEOUT => 8, CURLOPT_TIMEOUT => 120]);
        $ok = curl_exec($ch); $status = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE); curl_close($ch); fclose($handle);
        if (!$ok || $status < 200 || $status >= 300) { @unlink($destination . '.part'); throw new MusicTransientException('Falha ao baixar a capa do ComfyUI.'); }
        if (!rename($destination . '.part', $destination)) throw new RuntimeException('Falha ao concluir o arquivo da capa.');
    }
}
