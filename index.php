<?php
session_start();
if (isset($_SESSION['user_cpf'])) {
    header('Location: dashboard.php');
    exit;
}
$error = $_SESSION['login_error'] ?? '';
unset($_SESSION['login_error']);
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>eMusic Lite • Login</title>
  <link rel="stylesheet" href="assets/css/style.css" />
</head>
<body class="login-body">
  <div class="login-card">
    <div class="brand">
      <div class="brand-mark">eM</div>
      <div class="brand-text">
        <h1>eMusic Lite</h1>
        <p>Streaming de música para clientes do provedor</p>
      </div>
    </div>

    <?php if ($error): ?>
      <div class="alert error"><?php echo htmlspecialchars($error); ?></div>
    <?php endif; ?>

    <form class="login-form" method="POST" action="auth.php">
      <input type="hidden" name="login_csrf" value="<?php echo htmlspecialchars($_SESSION['login_csrf'] ??= bin2hex(random_bytes(32))); ?>" />
      <label for="cpf">CPF do cliente</label>
      <input id="cpf" name="cpf" type="text" placeholder="000.000.000-00" required />
      <button type="submit">Entrar</button>
      <p class="hint">Acesso liberado apenas com status ATIVO.</p>
    </form>
  </div>
</body>
</html>
