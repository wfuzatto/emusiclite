<?php

require_once __DIR__ . '/../../includes/db.php';
require_once __DIR__ . '/../../services/AudioValidationService.php';

function music_ingest_response(array $data, int $status = 200): void
{
    http_response_code($status); header('Content-Type: application/json; charset=utf-8'); header('Cache-Control: no-store');
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES); exit;
}

function music_handle_ingest(mysqli $db, string $expectedType): void
{
    if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') music_ingest_response(['ok'=>false,'message'=>'Método não permitido.'],405);
    $config = require __DIR__ . '/../../config/music_ai.php';
    if (strlen($config['ingest_secret']) < 32) {
        $config['ingest_secret'] = music_setting_local($db, 'worker_ingest_secret', '');
    }
    $forwarded = strtolower(trim(explode(',', (string) ($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? ''))[0]));
    $directHttps = !empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off';
    $remoteAddress = (string) ($_SERVER['REMOTE_ADDR'] ?? '');
    $localTlsProxy = in_array($remoteAddress, ['127.0.0.1', '::1'], true) && $forwarded === 'https';
    if (!$directHttps && !$localTlsProxy && !($config['trust_proxy_https'] && $forwarded === 'https')) music_ingest_response(['ok'=>false,'message'=>'HTTPS obrigatório.'],400);
    if (strlen($config['ingest_secret']) < 32) music_ingest_response(['ok'=>false,'message'=>'Serviço indisponível.'],503);
    $timestamp = (int) ($_POST['timestamp'] ?? 0); $requestId = (string) ($_POST['request_id'] ?? '');
    $trackId = (int) ($_POST['track_id'] ?? 0); $userId = (int) ($_POST['user_id'] ?? 0);
    $type = strtoupper((string) ($_POST['media_type'] ?? '')); $sha = strtolower((string) ($_POST['sha256'] ?? ''));
    $signature = strtolower((string) ($_POST['signature'] ?? ''));
    if ($type !== $expectedType || $trackId < 1 || $userId < 1 || !preg_match('/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i', $requestId)
        || !preg_match('/^[a-f0-9]{64}$/', $sha) || !preg_match('/^[a-f0-9]{64}$/', $signature)
        || abs(time() - $timestamp) > $config['ingest_max_skew']) music_ingest_response(['ok'=>false,'message'=>'Assinatura inválida.'],401);
    if (!isset($_FILES['file']) || ($_FILES['file']['error'] ?? UPLOAD_ERR_NO_FILE) !== UPLOAD_ERR_OK || !is_uploaded_file($_FILES['file']['tmp_name'])) music_ingest_response(['ok'=>false,'message'=>'Arquivo inválido.'],422);
    $actualSha = hash_file('sha256', $_FILES['file']['tmp_name']);
    $canonical = implode("\n", [$timestamp,$requestId,$trackId,$userId,$type,$actualSha]);
    $expected = hash_hmac('sha256', $canonical, $config['ingest_secret']);
    if (!hash_equals($sha, $actualSha) || !hash_equals($expected, $signature)) music_ingest_response(['ok'=>false,'message'=>'Assinatura inválida.'],401);

    $stmt = $db->prepare('SELECT id,desired_duration_seconds FROM music_ai_tracks WHERE id=? AND owner_user_id=? AND status<>\'DELETED\' LIMIT 1');
    $stmt->bind_param('ii', $trackId, $userId); $stmt->execute(); $track = $stmt->get_result()->fetch_assoc(); $stmt->close();
    if (!$track) music_ingest_response(['ok'=>false,'message'=>'Projeto não encontrado.'],404);
    $size = (int) filesize($_FILES['file']['tmp_name']); $mime = (new finfo(FILEINFO_MIME_TYPE))->file($_FILES['file']['tmp_name']) ?: '';
    $audioMimes = ['audio/mpeg'=>'mp3','audio/ogg'=>'ogg','audio/wav'=>'wav','audio/x-wav'=>'wav','audio/flac'=>'flac','audio/aac'=>'aac','audio/mp4'=>'m4a','video/mp4'=>'m4a'];
    $coverMimes = ['image/png'=>'png','image/jpeg'=>'jpg','image/webp'=>'webp'];
    $allowed = $type === 'AUDIO' ? $audioMimes : $coverMimes;
    $limitMb = $type === 'AUDIO' ? (int) music_setting_local($db, 'max_audio_mb', (string) $config['max_audio_mb']) : (int) music_setting_local($db, 'max_cover_mb', (string) $config['max_cover_mb']);
    if (!isset($allowed[$mime]) || $size < 1 || $size > $limitMb * 1024 * 1024) music_ingest_response(['ok'=>false,'message'=>'Tipo ou tamanho de arquivo inválido.'],422);
    $validation = json_decode((string) ($_POST['validation'] ?? ''), true) ?: [];
    $width = null; $height = null; $duration = null; $channels = null; $rate = null;
    if ($type === 'AUDIO') {
        try { $validation = (new AudioValidationService($config))->validate($_FILES['file']['tmp_name'], (int) $track['desired_duration_seconds']); }
        catch (Throwable $e) { music_ingest_response(['ok'=>false,'message'=>'O áudio não passou pela validação.'],422); }
        $duration = $validation['duration_seconds']; $channels = $validation['channels']; $rate = $validation['sample_rate'];
    } else {
        $image = @getimagesize($_FILES['file']['tmp_name']);
        if (!$image || $image[0] < 512 || $image[1] < 512 || $image[0] > 8192 || $image[1] > 8192) music_ingest_response(['ok'=>false,'message'=>'A capa não passou pela validação.'],422);
        $width = $image[0]; $height = $image[1]; $validation = array_merge($validation, ['width'=>$width,'height'=>$height]);
    }

    $db->begin_transaction(); $tempPath = null; $newFinalPath = null;
    try {
        $stmt = $db->prepare('INSERT INTO music_ai_ingest_requests(request_id,track_id,media_type) VALUES(?,?,?)');
        $stmt->bind_param('sis', $requestId, $trackId, $type);
        try { $stmt->execute(); $stmt->close(); } catch (mysqli_sql_exception $e) { $stmt->close(); if ((int)$e->getCode()===1062) { $db->rollback(); music_ingest_response(['ok'=>false,'message'=>'Requisição já utilizada.'],409); } throw $e; }
        $stmt = $db->prepare('SELECT id,checksum_sha256 FROM music_ai_media WHERE track_id=? AND media_type=? LIMIT 1');
        $stmt->bind_param('is', $trackId, $type); $stmt->execute(); $existing = $stmt->get_result()->fetch_assoc(); $stmt->close();
        if ($existing) {
            if (!hash_equals($existing['checksum_sha256'], $sha)) throw new DomainException('Já existe mídia diferente para este checkpoint.');
            $mediaId = (int) $existing['id'];
        } else {
            $dir = $config['public_media_path'] . '/' . $trackId;
            if (!is_dir($dir) && !mkdir($dir, 0750, true) && !is_dir($dir)) throw new RuntimeException('Falha de armazenamento.');
            $filename = strtolower($type) . '-' . substr($sha, 0, 24) . '.' . $allowed[$mime];
            $finalPath = $dir . '/' . $filename; $tempPath = $dir . '/.' . $requestId . '.part';
            if (!move_uploaded_file($_FILES['file']['tmp_name'], $tempPath) || !rename($tempPath, $finalPath)) throw new RuntimeException('Falha de armazenamento.');
            $tempPath = null; $newFinalPath = $finalPath; $validationJson = json_encode($validation, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
            $original = mb_substr((string) $_FILES['file']['name'], 0, 255);
            $stmt = $db->prepare('INSERT INTO music_ai_media(track_id,user_id,media_type,original_filename,stored_filename,mime_type,file_size,storage_path,checksum_sha256,duration_seconds,channels,sample_rate,width,height,validation_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)');
            $stmt->bind_param('iissssissdiiiis', $trackId, $userId, $type, $original, $filename, $mime, $size, $finalPath, $sha, $duration, $channels, $rate, $width, $height, $validationJson);
            $stmt->execute(); $mediaId = (int) $stmt->insert_id; $stmt->close();
        }
        $column = $type === 'AUDIO' ? 'audio_media_id' : 'cover_media_id';
        $checkpoint = $type === 'AUDIO' ? 'audio_uploaded_at' : 'cover_uploaded_at';
        $stmt = $db->prepare("UPDATE music_ai_tracks SET {$column}=?,{$checkpoint}=COALESCE({$checkpoint},NOW()) WHERE id=? AND owner_user_id=?");
        $stmt->bind_param('iii', $mediaId, $trackId, $userId); $stmt->execute(); $stmt->close();
        $stmt = $db->prepare('UPDATE music_ai_ingest_requests SET media_id=? WHERE request_id=?'); $stmt->bind_param('is', $mediaId, $requestId); $stmt->execute(); $stmt->close();
        $db->commit(); $newFinalPath = null; music_ingest_response(['ok'=>true,'media_id'=>$mediaId],201);
    } catch (DomainException $e) {
        $db->rollback(); if ($tempPath && is_file($tempPath)) @unlink($tempPath); if ($newFinalPath && is_file($newFinalPath)) @unlink($newFinalPath); music_ingest_response(['ok'=>false,'message'=>'Checkpoint de mídia conflitante.'],409);
    } catch (Throwable $e) {
        $db->rollback(); if ($tempPath && is_file($tempPath)) @unlink($tempPath); if ($newFinalPath && is_file($newFinalPath)) @unlink($newFinalPath); music_ingest_response(['ok'=>false,'message'=>'Não foi possível armazenar o arquivo.'],500);
    }
}

function music_setting_local(mysqli $db, string $key, string $fallback): string
{
    $stmt=$db->prepare('SELECT setting_value FROM music_ai_settings WHERE setting_key=? LIMIT 1');$stmt->bind_param('s',$key);$stmt->execute();$row=$stmt->get_result()->fetch_assoc();$stmt->close();return(string)($row['setting_value']??$fallback);
}
