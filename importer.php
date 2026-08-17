<?php
session_start();
if (!isset($_SESSION['user_cpf'])) {
    header('Location: index.php');
    exit;
}

$resultMsg = '';

function sql_escape($v) {
    $v = str_replace("\\", "\\\\", $v);
    $v = str_replace("'", "\\'", $v);
    return $v;
}

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $url = trim($_POST['url'] ?? '');
    $genre = trim($_POST['genre'] ?? 'Pop');
    $mood = trim($_POST['mood'] ?? 'Leve');
    $cover = trim($_POST['cover'] ?? '');
    $out = __DIR__ . '/import_tracks.sql';

    if ($url === '') {
        $resultMsg = 'Informe uma URL válida.';
    } else {
        $ctx = stream_context_create([
            'http' => ['timeout' => 20, 'header' => "User-Agent: eMusicLite/1.0\r\n"],
            'https' => ['timeout' => 20, 'header' => "User-Agent: eMusicLite/1.0\r\n"],
        ]);

        $text = @file_get_contents($url, false, $ctx);
        if ($text === false) {
            $resultMsg = 'Falha ao baixar o conteúdo da URL.';
        } else {
            // Try to parse simple metadata from a text file
            $title = '';
            $artist = '';
            if (preg_match('/^Title:\s*(.+)$/mi', $text, $m)) $title = trim($m[1]);
            if (preg_match('/^Artist:\s*(.+)$/mi', $text, $m)) $artist = trim($m[1]);
            if ($title === '') $title = 'Faixa importada';
            if ($artist === '') $artist = 'Artista desconhecido';

            $description = 'Importado por URL: ' . $url;
            $duration = '0:00';

            $insert = "INSERT INTO tracks (title, artist, genre, mood, description, duration, cover_url, stream_url) VALUES (" .
                "'" . sql_escape($title) . "', " .
                "'" . sql_escape($artist) . "', " .
                "'" . sql_escape($genre) . "', " .
                "'" . sql_escape($mood) . "', " .
                "'" . sql_escape($description) . "', " .
                "'" . sql_escape($duration) . "', " .
                "'" . sql_escape($cover) . "', " .
                "'" . sql_escape($url) . "');\n";

            if (!file_exists($out)) {
                @file_put_contents($out, '');
            }

            if (!is_writable($out)) {
                $resultMsg = 'Sem permissão para escrever em: ' . $out;
            } else {
                $written = @file_put_contents($out, $insert, FILE_APPEND | LOCK_EX);
                if ($written === false) {
                    $resultMsg = 'Falha ao escrever em: ' . $out;
                } else {
                    $resultMsg = 'Linha adicionada com sucesso em: ' . $out;
                }
            }
        }
    }
}
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>eMusic Lite • Importar por URL</title>
  <link rel="stylesheet" href="assets/css/style.css" />
</head>
<body class="app-body">
  <div class="app">
    <aside class="sidebar">
      <div class="logo">eMusic Lite</div>
      <nav>
        <a href="dashboard.php">Início</a>
        <a href="admin.php">Cadastro</a>
        <a href="importer.php" class="active">Importar por URL</a>
      </nav>
      <a class="logout" href="logout.php">Sair</a>
    </aside>

    <main class="main">
      <header class="topbar">
        <div>
          <h1>Importar por URL</h1>
          <p>Cole a URL de um áudio e gere a linha no SQL.</p>
        </div>
      </header>

      <section class="panel">
        <?php if ($resultMsg): ?>
          <div class="alert success"><?php echo htmlspecialchars($resultMsg); ?></div>
        <?php endif; ?>

        <form class="form-grid" method="POST">
          <div class="field full">
            <label for="url">URL do áudio (mp3/ogg)</label>
            <input id="url" name="url" type="url" required placeholder="https://" />
          </div>
          <div class="field">
            <label for="genre">Gênero</label>
            <input id="genre" name="genre" type="text" value="Pop" />
          </div>
          <div class="field">
            <label for="mood">Mood</label>
            <input id="mood" name="mood" type="text" value="Leve" />
          </div>
          <div class="field full">
            <label for="cover">URL da capa</label>
            <input id="cover" name="cover" type="url" placeholder="https://" />
          </div>
          <button type="submit">Gerar linha no SQL</button>
        </form>
      </section>
    </main>
  </div>
</body>
</html>
