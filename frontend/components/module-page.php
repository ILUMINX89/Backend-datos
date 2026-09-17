<?php
declare(strict_types=1);

if (!isset($pageTitle, $pageDescription, $pageSections) || !is_array($pageSections)) {
    throw new LogicException('La página del módulo requiere título, descripción y secciones.');
}
?>
<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>RKP | <?= htmlspecialchars($pageTitle, ENT_QUOTES, 'UTF-8') ?></title>
    <link rel="stylesheet" href="assets/css/style.css">
    <link rel="stylesheet" href="assets/css/sidebar.css">
    <link rel="stylesheet" href="assets/css/module-page.css">
</head>
<body class="gkp-page">
<div class="app">
    <?php require __DIR__ . '/sidebar.php'; ?>
    <main class="main">
        <?php require __DIR__ . '/header.php'; ?>
        <div class="module-content">
            <header class="module-heading">
                <h2><?= htmlspecialchars($pageTitle, ENT_QUOTES, 'UTF-8') ?></h2>
                <p><?= htmlspecialchars($pageDescription, ENT_QUOTES, 'UTF-8') ?></p>
            </header>
            <div class="module-sections">
                <?php foreach ($pageSections as $section): ?>
                    <section class="card module-panel" aria-labelledby="<?= htmlspecialchars($section['id'], ENT_QUOTES, 'UTF-8') ?>">
                        <h3 id="<?= htmlspecialchars($section['id'], ENT_QUOTES, 'UTF-8') ?>"><?= htmlspecialchars($section['title'], ENT_QUOTES, 'UTF-8') ?></h3>
                        <?php if (!empty($section['description'])): ?><p><?= htmlspecialchars($section['description'], ENT_QUOTES, 'UTF-8') ?></p><?php endif; ?>
                        <div class="module-empty" role="status">Sin datos disponibles</div>
                    </section>
                <?php endforeach; ?>
            </div>
        </div>
        <?php require __DIR__ . '/footer.php'; ?>
    </main>
</div>
<script src="assets/js/sidebar.js" defer></script>
</body>
</html>
