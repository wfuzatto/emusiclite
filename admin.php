<?php
session_start();
if (!isset($_SESSION['user_cpf'])) {
    header('Location: index.php');
    exit;
}
require __DIR__ . '/includes/db.php';

$success = $_SESSION['track_success'] ?? '';
$error = $_SESSION['track_error'] ?? '';
unset($_SESSION['track_success'], $_SESSION['track_error']);

$tracks = [];
$result = $mysqli->query('SELECT id, title, artist, genre, mood, duration, cover_url, description, stream_url FROM tracks ORDER BY created_at DESC');
if ($result) {
    while ($row = $result->fetch_assoc()) {
        $tracks[] = $row;
    }
}
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>eMusic Lite • Cadastro de Músicas</title>
  <link rel="stylesheet" href="assets/css/style.css" />
</head>
<body class="app-body">
  <div class="app">
    <aside class="sidebar">
      <div class="logo">eMusic Lite</div>
      <nav>
        <a href="dashboard.php">Início</a>
        <a href="admin.php" class="active">Cadastro</a>
        <a href="importer.php">Importar por URL</a>
      </nav>
      <a class="logout" href="logout.php">Sair</a>
    </aside>

    <main class="main">
      <header class="topbar">
        <div>
          <h1>Cadastro de músicas</h1>
          <p>Adicione faixas ao catálogo.</p>
        </div>
      </header>

      <?php if ($success): ?>
        <div class="alert success"><?php echo htmlspecialchars($success); ?></div>
      <?php endif; ?>
      <?php if ($error): ?>
        <div class="alert error"><?php echo htmlspecialchars($error); ?></div>
      <?php endif; ?>

      <section class="panel">
        <div class="panel-header">
          <h2>Faixas cadastradas</h2>
          <input id="trackSearch" class="search-inline" type="text" placeholder="Buscar por título, artista ou gênero" />
        </div>
        <div class="mini-grid" id="trackList">
          <?php foreach ($tracks as $track): ?>
            <div class="mini-card"
              data-id="<?php echo (int)$track['id']; ?>"
              data-title="<?php echo htmlspecialchars($track['title']); ?>"
              data-artist="<?php echo htmlspecialchars($track['artist']); ?>"
              data-genre="<?php echo htmlspecialchars($track['genre']); ?>"
              data-mood="<?php echo htmlspecialchars($track['mood']); ?>"
              data-duration="<?php echo htmlspecialchars($track['duration']); ?>"
              data-cover="<?php echo htmlspecialchars($track['cover_url']); ?>"
              data-description="<?php echo htmlspecialchars($track['description']); ?>"
              data-stream="<?php echo htmlspecialchars($track['stream_url']); ?>"
            >
              <div class="mini-cover" style="background-image: url('<?php echo htmlspecialchars($track['cover_url']); ?>');"></div>
              <div>
                <strong><?php echo htmlspecialchars($track['title']); ?></strong>
                <p><?php echo htmlspecialchars($track['artist']); ?> • <?php echo htmlspecialchars($track['genre']); ?></p>
              </div>
            </div>
          <?php endforeach; ?>
        </div>
        <div class="pager">
          <button id="prevPage">Anterior</button>
          <span id="pageInfo">1</span>
          <button id="nextPage">Próxima</button>
        </div>
      </section>
    </main>
  </div>

  <button class="plus-float" id="openModal" aria-label="Adicionar música">+</button>

  <div class="modal" id="trackModal" aria-hidden="true">
    <div class="modal-content">
      <div class="modal-header">
        <h3 id="modalTitle">Nova música</h3>
        <button class="modal-close" id="closeModal">×</button>
      </div>
      <form class="form-grid" method="POST" action="save_track.php" enctype="multipart/form-data">
        <input type="hidden" id="track_id" name="track_id" value="" />
        <div class="field">
          <label for="title">Título</label>
          <input id="title" name="title" type="text" required />
        </div>
        <div class="field">
          <label for="artist">Artista</label>
          <input id="artist" name="artist" type="text" required />
        </div>
        <div class="field">
          <label for="genre">Gênero</label>
          <input id="genre" name="genre" type="text" required />
        </div>
        <div class="field">
          <label for="mood">Mood</label>
          <input id="mood" name="mood" type="text" required />
        </div>
        <div class="field">
          <label for="duration">Duração (ex: 3:21)</label>
          <input id="duration" name="duration" type="text" required />
        </div>
        <div class="field">
          <label for="cover_url">URL da capa</label>
          <input id="cover_url" name="cover_url" type="url" placeholder="https://" required />
        </div>
        <div class="field full">
          <label for="description">Descrição</label>
          <textarea id="description" name="description" rows="3" required></textarea>
        </div>
        <div class="field full">
          <label for="stream_url">URL do áudio (mp3/ogg)</label>
          <input id="stream_url" name="stream_url" type="url" placeholder="https://" />
        </div>
        <div class="field full">
          <label for="audio_file">Upload do áudio (mp3/ogg)</label>
          <input id="audio_file" name="audio_file" type="file" accept="audio/mpeg,audio/ogg" />
          <small class="hint">Se enviar arquivo, ele será salvo em assets/audio/ e usado no player.</small>
        </div>
        <button type="submit">Salvar</button>
      </form>
    </div>
  </div>

  <script src="assets/js/admin.js"></script>
</body>
</html>
