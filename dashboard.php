<?php
session_start();
if (!isset($_SESSION['user_cpf'])) {
    header('Location: index.php');
    exit;
}
require __DIR__ . '/includes/bootstrap.php';
$musicUser = music_current_user($mysqli, true);

$tracks = [];
$result = $mysqli->query('SELECT id, title, artist, genre, mood, description, cover_url, duration, stream_url FROM tracks ORDER BY created_at DESC');
if ($result) {
    while ($row = $result->fetch_assoc()) {
        $tracks[] = $row;
    }
}
$aiResult = $mysqli->query("SELECT t.id,t.title,u.display_name artist,t.genre,t.mood,COALESCE(t.description,'') description,
  CONCAT('api/music/media.php?id=',t.cover_media_id) cover_url,
  SEC_TO_TIME(t.desired_duration_seconds) duration,
  CONCAT('api/music/media.php?id=',t.audio_media_id) stream_url
  FROM music_ai_tracks t JOIN music_ai_users u ON u.id=t.owner_user_id
  WHERE t.status='COMPLETED' AND t.is_published=1 AND t.audio_media_id IS NOT NULL AND t.cover_media_id IS NOT NULL
  ORDER BY t.published_at DESC");
if($aiResult){while($row=$aiResult->fetch_assoc())$tracks[]=$row;}
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>eMusic Lite • Dashboard</title>
  <link rel="stylesheet" href="assets/css/style.css" />
</head>
<body class="app-body">
  <div class="app">
    <aside class="sidebar">
      <div class="logo">eMusic Lite</div>
      <nav>
        <a class="active" href="dashboard.php">Início</a>
        <a href="criar-musica.php">Criar com IA</a>
        <a href="minhas-musicas.php">Minhas músicas</a>
        <?php if (isset($_GET['admin']) && $_GET['admin'] === '1'): ?>
          <a href="admin.php">Cadastro</a>
          <a href="importer.php">Importar por URL</a>
        <?php endif; ?>
        <?php if (music_is_admin((int)$musicUser['id'])): ?><a href="ai-agent.php">Agente musical</a><?php endif; ?>
      </nav>
      <div class="playlist">
        <h4>Playlists</h4>
        <ul>
          <li>Daily Boost</li>
          <li>Noite Neon</li>
          <li>Chill Tropical</li>
          <li>Foco Total</li>
          <li>Clássicos Urbanos</li>
        </ul>
      </div>
      <a class="logout" href="logout.php">Sair</a>
    </aside>

    <main class="main">
      <header class="topbar">
        <div>
          <h1>Boa noite</h1>
          <p>Continue ouvindo as suas descobertas favoritas.</p>
        </div>
        <div class="search">
          <input id="searchInput" type="text" placeholder="Buscar por música, artista ou gênero" />
        </div>
      </header>

      <section class="grid" id="trackGrid">
        <?php foreach ($tracks as $track): ?>
          <article class="track-card"
            data-title="<?php echo htmlspecialchars(mb_strtolower($track['title'])); ?>"
            data-artist="<?php echo htmlspecialchars(mb_strtolower($track['artist'])); ?>"
            data-genre="<?php echo htmlspecialchars(mb_strtolower($track['genre'])); ?>"
            data-mood="<?php echo htmlspecialchars(mb_strtolower($track['mood'])); ?>"
            data-description="<?php echo htmlspecialchars($track['description']); ?>"
            data-duration="<?php echo htmlspecialchars($track['duration']); ?>"
            data-stream="<?php echo htmlspecialchars($track['stream_url']); ?>"
            data-cover="<?php echo htmlspecialchars($track['cover_url']); ?>">
            <div class="cover" style="background-image: url('<?php echo htmlspecialchars($track['cover_url']); ?>');"></div>
            <div class="meta">
              <h3><?php echo htmlspecialchars($track['title']); ?></h3>
              <p><?php echo htmlspecialchars($track['artist']); ?> • <?php echo htmlspecialchars($track['genre']); ?></p>
              <span><?php echo htmlspecialchars($track['mood']); ?></span>
            </div>
          </article>
        <?php endforeach; ?>
      </section>
    </main>

    <footer class="player">
      <div class="now">
        <div class="now-cover" id="nowCover"></div>
        <div>
          <strong id="nowTitle">Selecione uma música</strong>
          <p id="nowArtist">eMusic Lite</p>
        </div>
      </div>
      <div class="controls">
        <button id="prevBtn" aria-label="Anterior">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 6h2v12H7V6zm3.5 6L20 18V6l-9.5 6z"/></svg>
        </button>
        <button class="play" id="playBtn" aria-label="Play/Pause">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5v14l11-7L8 5z"/></svg>
        </button>
        <button id="nextBtn" aria-label="Próxima">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 6h2v12h-2V6zM4 18V6l9.5 6L4 18z"/></svg>
        </button>
      </div>
      <div class="progress">
        <span id="nowTime">0:00</span>
        <div class="bar" id="progressBar"><div class="fill" id="nowFill"></div></div>
        <span id="nowDuration">0:00</span>
      </div>
      <audio id="audio" preload="none"></audio>
    </footer>
  </div>

  <script>const TRACKS = <?php echo json_encode($tracks, JSON_UNESCAPED_UNICODE); ?>;</script>
  <script src="assets/js/app.js"></script>
</body>
</html>
