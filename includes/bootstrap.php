<?php

if (session_status() !== PHP_SESSION_ACTIVE && PHP_SAPI !== 'cli') {
    session_start();
}

require_once __DIR__ . '/db.php';

function music_e(string $value): string
{
    return htmlspecialchars($value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function music_config(): array
{
    global $mysqli;
    static $config;
    if (isset($config)) return $config;
    $config = require __DIR__ . '/../config/music_ai.php';
    if (strlen($config['ingest_secret']) < 32 && isset($mysqli)) {
        $key = 'worker_ingest_secret';
        $stmt = $mysqli->prepare('SELECT setting_value FROM music_ai_settings WHERE setting_key=? LIMIT 1');
        $stmt->bind_param('s', $key);
        $stmt->execute();
        $row = $stmt->get_result()->fetch_assoc();
        $stmt->close();
        $stored = (string) ($row['setting_value'] ?? '');
        if (strlen($stored) >= 32) $config['ingest_secret'] = $stored;
    }
    return $config;
}

function music_csrf_token(): string
{
    if (empty($_SESSION['music_csrf_token'])) {
        $_SESSION['music_csrf_token'] = bin2hex(random_bytes(32));
    }
    return $_SESSION['music_csrf_token'];
}

function music_verify_csrf(?string $token): bool
{
    return is_string($token) && isset($_SESSION['music_csrf_token'])
        && hash_equals($_SESSION['music_csrf_token'], $token);
}

function music_json(array $data, int $status = 200): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function music_api_post(): void
{
    if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
        music_json(['ok' => false, 'message' => 'Método não permitido.'], 405);
    }
}

function music_api_csrf(): void
{
    $token = $_SERVER['HTTP_X_CSRF_TOKEN'] ?? ($_POST['csrf_token'] ?? null);
    if (!music_verify_csrf($token)) {
        music_json(['ok' => false, 'message' => 'Sessão expirada. Atualize a página.'], 419);
    }
}

function music_current_user(mysqli $db, bool $required = true): ?array
{
    $cpf = preg_replace('/\D+/', '', (string) ($_SESSION['user_cpf'] ?? ''));
    if (strlen($cpf) !== 11) {
        if ($required) music_json(['ok' => false, 'message' => 'Acesso não autorizado.'], 401);
        return null;
    }
    $config = music_config();
    $key = $config['subject_key'];
    $subject = $key !== '' ? hash_hmac('sha256', $cpf, $key) : hash('sha256', 'emusiclite:' . $cpf);
    $name = 'Cliente ' . substr($subject, 0, 6);
    $stmt = $db->prepare(
        "INSERT INTO music_ai_users (external_subject_hash,display_name,internal_code,user_type,status)
         VALUES (?,?,NULL,'CUSTOMER','ACTIVE')
         ON DUPLICATE KEY UPDATE id=LAST_INSERT_ID(id),status=IF(status='SYSTEM',status,'ACTIVE')"
    );
    $stmt->bind_param('ss', $subject, $name);
    $stmt->execute();
    $id = (int) $db->insert_id;
    $stmt->close();
    $stmt = $db->prepare('SELECT id,display_name,user_type,status FROM music_ai_users WHERE id=? LIMIT 1');
    $stmt->bind_param('i', $id);
    $stmt->execute();
    $user = $stmt->get_result()->fetch_assoc();
    $stmt->close();
    if (!$user || $user['status'] !== 'ACTIVE') {
        if ($required) music_json(['ok' => false, 'message' => 'Acesso não autorizado.'], 401);
        return null;
    }
    return $user;
}

function music_require_page_user(mysqli $db): array
{
    if (empty($_SESSION['user_cpf'])) {
        header('Location: index.php');
        exit;
    }
    return music_current_user($db, true);
}

function music_require_owned_track(mysqli $db, int $trackId, int $userId): array
{
    $stmt = $db->prepare('SELECT * FROM music_ai_tracks WHERE id=? AND owner_user_id=? LIMIT 1');
    $stmt->bind_param('ii', $trackId, $userId);
    $stmt->execute();
    $track = $stmt->get_result()->fetch_assoc();
    $stmt->close();
    if (!$track) music_json(['ok' => false, 'message' => 'Música não encontrada.'], 404);
    return $track;
}

function music_is_admin(int $userId): bool
{
    return in_array($userId, music_config()['admin_user_ids'], true);
}

function music_require_admin(mysqli $db): array
{
    $user = music_current_user($db, true);
    if (!music_is_admin((int) $user['id'])) {
        if (PHP_SAPI === 'cli') throw new RuntimeException('Administrador não autorizado.');
        http_response_code(403);
        exit('Acesso não autorizado.');
    }
    return $user;
}

function music_setting(mysqli $db, string $key, string $fallback = ''): string
{
    $stmt = $db->prepare('SELECT setting_value FROM music_ai_settings WHERE setting_key=? LIMIT 1');
    $stmt->bind_param('s', $key);
    $stmt->execute();
    $row = $stmt->get_result()->fetch_assoc();
    $stmt->close();
    return (string) ($row['setting_value'] ?? $fallback);
}

function music_rate_limit(mysqli $db, int $userId, string $operation, int $seconds = 8): void
{
    $operation = 'rate:' . mb_substr($operation, 0, 55);
    $stmt = $db->prepare("SELECT id FROM music_ai_logs WHERE user_id=? AND operation=? AND status='rate' AND created_at>=DATE_SUB(NOW(),INTERVAL ? SECOND) LIMIT 1");
    $stmt->bind_param('isi', $userId, $operation, $seconds);
    $stmt->execute();
    $limited = (bool) $stmt->get_result()->fetch_assoc();
    $stmt->close();
    if ($limited) music_json(['ok' => false, 'message' => 'Aguarde alguns segundos antes de tentar novamente.'], 429);
    $stmt = $db->prepare("INSERT INTO music_ai_logs(user_id,operation,status) VALUES(?,?,'rate')");
    $stmt->bind_param('is', $userId, $operation);
    $stmt->execute();
    $stmt->close();
}
