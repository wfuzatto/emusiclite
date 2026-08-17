<?php
session_start();

if ($_SERVER['REQUEST_METHOD'] !== 'POST'
    || empty($_POST['login_csrf']) || empty($_SESSION['login_csrf'])
    || !hash_equals($_SESSION['login_csrf'], (string) $_POST['login_csrf'])) {
    $_SESSION['login_error'] = 'Sessão expirada. Atualize a página e tente novamente.';
    header('Location: index.php');
    exit;
}

$cpf_raw = $_REQUEST['cpf'] ?? '';
$cpf = preg_replace('/\D+/', '', $cpf_raw);
$cpf_send = trim($cpf_raw) !== '' ? trim($cpf_raw) : $cpf;

if (strlen($cpf) !== 11) {
    $_SESSION['login_error'] = 'CPF inválido. Verifique e tente novamente.';
    header('Location: index.php');
    exit;
}

$endpoint = 'https://prodatastelecom.com.br/sites/netcontrol/sistema/acoes/consultacpfcliente.php';
$url = $endpoint . '?' . http_build_query(['cpf' => $cpf_send]);

$ch = curl_init($url);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
curl_setopt($ch, CURLOPT_TIMEOUT, 20);
curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
curl_setopt($ch, CURLOPT_USERAGENT, 'eMusicLite/1.0');
$response = curl_exec($ch);
$http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($response === false || $http_code >= 400) {
    $_SESSION['login_error'] = 'Não foi possível consultar o CPF no momento. Tente novamente.';
    header('Location: index.php');
    exit;
}

if ($response === '' || $response === null) {
    $context = stream_context_create([
        'http' => [
            'timeout' => 10,
            'header' => "User-Agent: eMusicLite/1.0\r\n"
        ]
    ]);
    $fallback = @file_get_contents($url, false, $context);
    if ($fallback !== false) {
        $response = $fallback;
    }
}

$isActive = false;
if (stripos((string)$response, 'ATIVO') !== false) {
    $isActive = true;
} else {
    $data = json_decode($response, true);
    if (is_array($data)) {
        foreach ($data as $row) {
            if (is_array($row)) {
                foreach ($row as $value) {
                    if (strtoupper(trim((string)$value)) === 'ATIVO') {
                        $isActive = true;
                        break 2;
                    }
                }
            } elseif (strtoupper(trim((string)$row)) === 'ATIVO') {
                $isActive = true;
                break;
            }
        }
    }
}

if (!$isActive) {
    $_SESSION['login_error'] = 'ENTRAR EM CONTATO COM A CENTRAL';
    header('Location: index.php');
    exit;
}

$_SESSION['user_cpf'] = $cpf;
unset($_SESSION['login_csrf']);
session_regenerate_id(true);
header('Location: dashboard.php');
exit;
