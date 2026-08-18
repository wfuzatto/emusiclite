<?php

require_once __DIR__ . '/MusicGenerationService.php';
require_once __DIR__ . '/MusicExceptions.php';

class HttpMusicGenerationService implements MusicGenerationService
{
    public function __construct(private array $config) {}
    public function backendName(): string { return 'http'; }

    public function healthCheck(): array
    {
        if ($this->config['music_backend_url'] === '') return ['online' => false, 'configured' => false, 'backend' => 'http'];
        try {
            $ch = curl_init($this->config['music_backend_url'] . '/health');
            curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_CONNECTTIMEOUT => 5, CURLOPT_TIMEOUT => 8]);
            $this->setAuth($ch, $this->config['music_backend_token']); curl_exec($ch); $status = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE); curl_close($ch);
            return ['online' => $status >= 200 && $status < 300, 'configured' => true, 'backend' => 'http'];
        } catch (Throwable $e) { return ['online' => false, 'configured' => true, 'backend' => 'http']; }
    }

    public function generate(array $specification, string $destinationPath): array
    {
        $model = (string)($specification['generation_model'] ?? 'turbo');
        $backend = $this->selectBackend($model);
        if ($backend['url'] === '') throw new MusicPermanentException($backend['missing_message']);
        $ch = curl_init($backend['url'] . '/generate');
        $headers = ['Content-Type: application/json', 'Accept: application/json'];
        if ($backend['token'] !== '') $headers[] = 'Authorization: Bearer ' . $backend['token'];
        curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_POST => true, CURLOPT_POSTFIELDS => json_encode($specification, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES), CURLOPT_HTTPHEADER => $headers, CURLOPT_CONNECTTIMEOUT => 10, CURLOPT_TIMEOUT => $backend['timeout']]);
        $body = curl_exec($ch); $status = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE); $error = curl_error($ch); curl_close($ch);
        if ($body === false || $status < 200 || $status >= 300) {
            $detail = $this->extractErrorDetail($body);
            if ($status >= 400 && $status < 500 && !in_array($status, [408, 409, 429], true)) throw new MusicPermanentException($detail !== '' ? $detail : 'O gerador rejeitou os parâmetros desta música.');
            $message = $detail !== '' ? $detail : ($error ? $error : 'Gerador musical indisponível.');
            throw new MusicTransientException($message);
        }
        $result = json_decode($body, true);
        $url = is_array($result) ? (string) ($result['audio_url'] ?? '') : '';
        if ($url === '' || !preg_match('#^https?://#i', $url)) throw new MusicTransientException('Gerador musical não retornou audio_url válido.');
        $this->download($url, $destinationPath, $backend['token'], $backend['timeout']);
        return ['backend' => $backend['name'], 'backend_job_id' => (string) ($result['job_id'] ?? ''), 'model' => (string)($result['model'] ?? $model), 'stems' => $result['stems'] ?? null, 'path' => $destinationPath];
    }

    private function selectBackend(string $model): array
    {
        if ($model === 'stable_audio') {
            return [
                'name' => 'stable-audio',
                'url' => (string)($this->config['stable_audio_url'] ?? ''),
                'token' => (string)($this->config['stable_audio_token'] ?? ''),
                'timeout' => (int)($this->config['stable_audio_timeout'] ?? 3600),
                'missing_message' => 'MUSIC_AI_STABLE_AUDIO_URL não foi configurada.',
            ];
        }
        if ($model === 'studio_midi') {
            return [
                'name' => 'studio-midi-sampled',
                'url' => (string)($this->config['studio_url'] ?? ''),
                'token' => (string)($this->config['studio_token'] ?? ''),
                'timeout' => (int)($this->config['studio_timeout'] ?? 1800),
                'missing_message' => 'MUSIC_AI_STUDIO_URL não foi configurada.',
            ];
        }
        return [
            'name' => 'ace-step',
            'url' => (string)$this->config['music_backend_url'],
            'token' => (string)$this->config['music_backend_token'],
            'timeout' => (int)$this->config['music_backend_timeout'],
            'missing_message' => 'MUSIC_AI_GENERATOR_URL não foi configurada.',
        ];
    }

    private function extractErrorDetail($body): string
    {
        if (!is_string($body) || trim($body) === '') return '';
        $decoded = json_decode($body, true);
        if (!is_array($decoded)) return '';
        $detail = $decoded['detail'] ?? $decoded['message'] ?? '';
        if (is_array($detail)) $detail = json_encode($detail, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        return is_string($detail) ? trim($detail) : '';
    }

    private function download(string $url, string $destination, string $token, int $timeout): void
    {
        $handle = fopen($destination . '.part', 'wb');
        if (!$handle) throw new RuntimeException('Não foi possível abrir o arquivo temporário de áudio.');
        $ch = curl_init($url);
        curl_setopt_array($ch, [CURLOPT_FILE => $handle, CURLOPT_FOLLOWLOCATION => true, CURLOPT_CONNECTTIMEOUT => 10, CURLOPT_TIMEOUT => $timeout]);
        $this->setAuth($ch, $token); $ok = curl_exec($ch); $status = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE); $error = curl_error($ch); curl_close($ch); fclose($handle);
        if (!$ok || $status < 200 || $status >= 300 || !is_file($destination . '.part') || filesize($destination . '.part') < 1024) { @unlink($destination . '.part'); throw new MusicTransientException('Falha ao baixar o áudio gerado' . ($error ? ': ' . $error : '.')); }
        if (!rename($destination . '.part', $destination)) throw new RuntimeException('Falha ao concluir o arquivo de áudio.');
    }

    private function setAuth($ch, string $token): void
    {
        if ($token !== '') curl_setopt($ch, CURLOPT_HTTPHEADER, ['Authorization: Bearer ' . $token]);
    }
}
