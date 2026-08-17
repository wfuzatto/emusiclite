<?php

require __DIR__ . '/../../includes/bootstrap.php';

function music_media_not_found(): never
{
    http_response_code(404);
    header('Content-Type: text/plain; charset=utf-8');
    header('Cache-Control: no-store');
    exit('Mídia não encontrada.');
}

function music_media_range_not_satisfiable(int $size): never
{
    http_response_code(416);
    header("Content-Range: bytes */{$size}");
    header('Cache-Control: no-store');
    exit;
}

function music_media_is_inside(string $path, string $root): bool
{
    $rootStat = @stat($root);
    if ($rootStat === false) return false;

    $directory = dirname($path);
    while (true) {
        $directoryStat = @stat($directory);
        if ($directoryStat !== false
            && $directoryStat['dev'] === $rootStat['dev']
            && $directoryStat['ino'] === $rootStat['ino']) {
            return true;
        }
        $parent = dirname($directory);
        if ($parent === $directory) return false;
        $directory = $parent;
    }
}

$id = filter_input(INPUT_GET, 'id', FILTER_VALIDATE_INT, [
    'options' => ['min_range' => 1],
]);
if (!$id) music_media_not_found();

$stmt = $mysqli->prepare(
    "SELECT m.*, t.owner_user_id, t.status AS track_status, t.is_published
       FROM music_ai_media m
       JOIN music_ai_tracks t ON t.id=m.track_id
      WHERE m.id=? AND m.media_type IN ('AUDIO','COVER') AND t.status<>'DELETED'
      LIMIT 1"
);
$stmt->bind_param('i', $id);
$stmt->execute();
$media = $stmt->get_result()->fetch_assoc();
$stmt->close();
if (!$media) music_media_not_found();

$isPublic = $media['track_status'] === 'COMPLETED' && (int) $media['is_published'] === 1;
if (!$isPublic) {
    $user = music_current_user($mysqli, false);
    if (!$user || (int) $media['owner_user_id'] !== (int) $user['id']) {
        music_media_not_found();
    }
}

$config = music_config();
$root = realpath((string) $config['public_media_path']);
$path = realpath((string) $media['storage_path']);
if (!$root || !$path || !music_media_is_inside($path, $root) || !is_file($path) || !is_readable($path)) {
    music_media_not_found();
}

$size = filesize($path);
if ($size === false || $size < 1) music_media_not_found();

$start = 0;
$end = $size - 1;
$range = trim((string) ($_SERVER['HTTP_RANGE'] ?? ''));
if ($range !== '') {
    if (!preg_match('/^bytes=(\d*)-(\d*)$/', $range, $matches) || ($matches[1] === '' && $matches[2] === '')) {
        music_media_range_not_satisfiable($size);
    }

    if ($matches[1] === '') {
        $suffixLength = (int) $matches[2];
        if ($suffixLength < 1) music_media_range_not_satisfiable($size);
        $start = max(0, $size - $suffixLength);
    } else {
        $start = (int) $matches[1];
        if ($start >= $size) music_media_range_not_satisfiable($size);
        if ($matches[2] !== '') $end = min((int) $matches[2], $end);
        if ($end < $start) music_media_range_not_satisfiable($size);
    }
    http_response_code(206);
    header("Content-Range: bytes {$start}-{$end}/{$size}");
}

$mime = strtolower((string) $media['mime_type']);
if ($mime === 'audio/x-wav' || $mime === 'audio/vnd.wave') $mime = 'audio/wav';
$allowedMimes = [
    'audio/wav', 'audio/mpeg', 'audio/ogg', 'audio/flac', 'audio/aac', 'audio/mp4',
    'image/png', 'image/jpeg', 'image/webp',
];
if (!in_array($mime, $allowedMimes, true)) music_media_not_found();

$handle = fopen($path, 'rb');
if ($handle === false || fseek($handle, $start) !== 0) music_media_not_found();

if (session_status() === PHP_SESSION_ACTIVE) session_write_close();
header_remove('Pragma');
header_remove('Expires');
header('Content-Type: ' . $mime);
header('Content-Disposition: inline');
header('X-Content-Type-Options: nosniff');
header('Accept-Ranges: bytes');
header('Cache-Control: ' . ($isPublic ? 'public' : 'private') . ', max-age=3600');
$length = $end - $start + 1;
header('Content-Length: ' . $length);

if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'HEAD') {
    fclose($handle);
    exit;
}

while (ob_get_level() > 0) ob_end_clean();
$remaining = $length;
while ($remaining > 0 && !feof($handle)) {
    $chunk = fread($handle, min(65536, $remaining));
    if ($chunk === false || $chunk === '') break;
    echo $chunk;
    $remaining -= strlen($chunk);
    flush();
}
fclose($handle);
