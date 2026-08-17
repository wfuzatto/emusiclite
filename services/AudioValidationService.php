<?php

require_once __DIR__ . '/MusicExceptions.php';

class AudioValidationService
{
    public function __construct(private array $config) {}

    public function validate(string $path, int $desiredSeconds): array
    {
        if (!is_file($path) || filesize($path) < 1024) throw new MusicPermanentException('O gerador produziu um arquivo de áudio vazio.');
        $limit = $this->config['max_audio_mb'] * 1024 * 1024;
        if (filesize($path) > $limit) throw new MusicPermanentException('O áudio excede o tamanho permitido.');
        $bin = $this->config['ffprobe'];
        if (!is_executable($bin)) throw new MusicPermanentException('ffprobe não foi encontrado na configuração do worker.');
        $command = escapeshellarg($bin) . ' -v error -show_entries format=format_name,duration,size -show_entries stream=codec_type,codec_name,sample_rate,channels -of json ' . escapeshellarg($path) . ' 2>&1';
        exec($command, $lines, $code);
        $data = json_decode(implode("\n", $lines), true);
        if ($code !== 0 || !is_array($data)) throw new MusicPermanentException('O arquivo de áudio está corrompido ou não é reproduzível.');
        $audio = null;
        foreach ($data['streams'] ?? [] as $stream) if (($stream['codec_type'] ?? '') === 'audio') { $audio = $stream; break; }
        $duration = (float) ($data['format']['duration'] ?? 0);
        $format = (string) ($data['format']['format_name'] ?? '');
        $allowed = ['mp3','wav','flac','ogg','opus','aac','m4a','mov,mp4,m4a,3gp,3g2,mj2'];
        if (!$audio || $duration <= 0 || !in_array($format, $allowed, true)) throw new MusicPermanentException('Formato ou stream de áudio inválido.');
        if ($duration < max(10, $desiredSeconds * 0.5) || $duration > $desiredSeconds * 1.5 + 15) throw new MusicPermanentException('A duração do áudio ficou fora da tolerância configurada.');
        $channels = (int) ($audio['channels'] ?? 0); $rate = (int) ($audio['sample_rate'] ?? 0);
        if ($channels < 1 || $channels > 8 || $rate < 22050 || $rate > 192000) throw new MusicPermanentException('Canais ou sample rate do áudio são inválidos.');
        return ['format' => $format, 'codec' => (string) ($audio['codec_name'] ?? ''), 'duration_seconds' => $duration, 'size' => filesize($path), 'channels' => $channels, 'sample_rate' => $rate, 'sha256' => hash_file('sha256', $path)];
    }
}
