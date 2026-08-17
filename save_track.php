<?php
session_start();
if (!isset($_SESSION['user_cpf'])) {
    header('Location: index.php');
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Location: admin.php');
    exit;
}

require __DIR__ . '/includes/db.php';

$track_id = (int)($_POST['track_id'] ?? 0);
$title = trim($_POST['title'] ?? '');
$artist = trim($_POST['artist'] ?? '');
$genre = trim($_POST['genre'] ?? '');
$mood = trim($_POST['mood'] ?? '');
$description = trim($_POST['description'] ?? '');
$duration = trim($_POST['duration'] ?? '');
$cover_url = trim($_POST['cover_url'] ?? '');
$stream_url = trim($_POST['stream_url'] ?? '');

$uploadPath = __DIR__ . '/assets/audio/';
$uploadedUrl = '';
if (!empty($_FILES['audio_file']['name'])) {
    if (!is_dir($uploadPath)) {
        @mkdir($uploadPath, 0777, true);
    }
    if (!is_writable($uploadPath)) {
        $_SESSION['track_error'] = 'Sem permissão para gravar em assets/audio/.';
        header('Location: admin.php');
        exit;
    }

    if (!empty($_FILES['audio_file']['error']) && $_FILES['audio_file']['error'] !== UPLOAD_ERR_OK) {
        $_SESSION['track_error'] = 'Falha no upload do áudio (código ' . $_FILES['audio_file']['error'] . ').';
        header('Location: admin.php');
        exit;
    }

    $allowed = ['audio/mpeg' => 'mp3', 'audio/ogg' => 'ogg', 'audio/mp3' => 'mp3'];
    $mime = '';
    if (function_exists('finfo_open')) {
        $finfo = finfo_open(FILEINFO_MIME_TYPE);
        $mime = $finfo ? finfo_file($finfo, $_FILES['audio_file']['tmp_name']) : '';
        if ($finfo) finfo_close($finfo);
    } else {
        $mime = $_FILES['audio_file']['type'] ?? '';
    }

    if (isset($allowed[$mime])) {
        $ext = $allowed[$mime];
        $safeName = preg_replace('/[^a-zA-Z0-9-_]/', '_', pathinfo($_FILES['audio_file']['name'], PATHINFO_FILENAME));
        $fileName = $safeName . '_' . time() . '.' . $ext;
        if (move_uploaded_file($_FILES['audio_file']['tmp_name'], $uploadPath . $fileName)) {
            $uploadedUrl = 'assets/audio/' . $fileName;
        } else {
            $_SESSION['track_error'] = 'Falha ao mover o arquivo enviado.';
            header('Location: admin.php');
            exit;
        }
    } else {
        $_SESSION['track_error'] = 'Tipo de arquivo inválido. Use MP3 ou OGG.';
        header('Location: admin.php');
        exit;
    }
}

if ($title === '' || $artist === '' || $genre === '' || $mood === '' || $description === '' || $duration === '' || $cover_url === '') {
    $_SESSION['track_error'] = 'Preencha todos os campos obrigatórios.';
    header('Location: admin.php');
    exit;
}

$finalStream = $uploadedUrl !== '' ? $uploadedUrl : $stream_url;

if ($track_id > 0) {
    $stmt = $mysqli->prepare('UPDATE tracks SET title=?, artist=?, genre=?, mood=?, description=?, duration=?, cover_url=?, stream_url=? WHERE id=?');
    if (!$stmt) {
        $_SESSION['track_error'] = 'Erro ao preparar a atualização.';
        header('Location: admin.php');
        exit;
    }
    $stmt->bind_param('ssssssssi', $title, $artist, $genre, $mood, $description, $duration, $cover_url, $finalStream, $track_id);
    if ($stmt->execute()) {
        $_SESSION['track_success'] = 'Música atualizada com sucesso.';
    } else {
        $_SESSION['track_error'] = 'Erro ao atualizar a música.';
    }
    $stmt->close();
} else {
    $stmt = $mysqli->prepare('INSERT INTO tracks (title, artist, genre, mood, description, duration, cover_url, stream_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?)');
    if (!$stmt) {
        $_SESSION['track_error'] = 'Erro ao preparar o cadastro.';
        header('Location: admin.php');
        exit;
    }
    $stmt->bind_param('ssssssss', $title, $artist, $genre, $mood, $description, $duration, $cover_url, $finalStream);
    if ($stmt->execute()) {
        $_SESSION['track_success'] = 'Música cadastrada com sucesso.';
    } else {
        $_SESSION['track_error'] = 'Erro ao salvar a música.';
    }
    $stmt->close();
}

header('Location: admin.php');
exit;
