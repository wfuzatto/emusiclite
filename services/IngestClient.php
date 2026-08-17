<?php

require_once __DIR__ . '/MusicExceptions.php';

class IngestClient
{
    public function __construct(private array $config) {}

    public function upload(string $type, int $trackId, int $userId, string $path, array $validation = []): int
    {
        if (!in_array($type, ['AUDIO','COVER'], true)) throw new InvalidArgumentException('Tipo de ingestão inválido.');
        if ($this->config['ingest_url'] === '') throw new MusicPermanentException('MUSIC_AI_INGEST_URL não foi configurada.');
        if (strlen($this->config['ingest_secret']) < 32) throw new MusicPermanentException('MUSIC_AI_INGEST_SECRET deve possuir pelo menos 32 caracteres.');
        if (!is_file($path)) throw new MusicPermanentException('Arquivo de ingestão não encontrado.');
        $timestamp = time(); $requestId = $this->uuid(); $sha = hash_file('sha256', $path);
        $canonical = implode("\n", [$timestamp,$requestId,$trackId,$userId,$type,$sha]);
        $signature = hash_hmac('sha256', $canonical, $this->config['ingest_secret']);
        $endpoint = $type === 'AUDIO' ? '/worker-audio-ingest.php' : '/worker-cover-ingest.php';
        $mime = (new finfo(FILEINFO_MIME_TYPE))->file($path) ?: 'application/octet-stream';
        $fields = [
            'timestamp' => (string) $timestamp, 'request_id' => $requestId, 'track_id' => (string) $trackId,
            'user_id' => (string) $userId, 'media_type' => $type, 'sha256' => $sha, 'signature' => $signature,
            'validation' => json_encode($validation, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES),
            'file' => new CURLFile($path, $mime, basename($path)),
        ];
        $ch = curl_init($this->config['ingest_url'] . $endpoint);
        $options = [CURLOPT_RETURNTRANSFER => true, CURLOPT_POST => true, CURLOPT_POSTFIELDS => $fields, CURLOPT_CONNECTTIMEOUT => 10, CURLOPT_TIMEOUT => 300, CURLOPT_HTTPHEADER => ['Accept: application/json']];
        if (($this->config['ingest_ca_file'] ?? '') !== '') $options[CURLOPT_CAINFO] = $this->config['ingest_ca_file'];
        curl_setopt_array($ch, $options);
        $body = curl_exec($ch); $status = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE); curl_close($ch);
        $result = json_decode((string) $body, true);
        if ($body === false || $status < 200 || $status >= 300 || !is_array($result) || empty($result['media_id'])) throw new MusicTransientException('A hospedagem não confirmou a ingestão do arquivo.');
        return (int) $result['media_id'];
    }

    private function uuid(): string
    {
        $data = random_bytes(16); $data[6] = chr((ord($data[6]) & 0x0f) | 0x40); $data[8] = chr((ord($data[8]) & 0x3f) | 0x80);
        return vsprintf('%s%s-%s-%s-%s-%s%s%s', str_split(bin2hex($data), 4));
    }
}
