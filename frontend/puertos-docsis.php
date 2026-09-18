<?php declare(strict_types=1); ?>
<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>RKP | Puertos DOCSIS</title>
    <link rel="stylesheet" href="assets/css/style.css">
    <link rel="stylesheet" href="assets/css/sidebar.css">
    <link rel="stylesheet" href="assets/css/gkp.css">
    <link rel="stylesheet" href="assets/css/module-page.css">
</head>
<body class="gkp-page hfc-page">
<div class="app">
    <?php require __DIR__ . '/components/sidebar.php'; ?>
    <main class="main">
        <?php require __DIR__ . '/components/header.php'; ?>
        <div class="module-content">
            <header class="module-heading">
                <h2>Puertos DOCSIS</h2>
                <p>Consulta y seguimiento operacional de puertos DOCSIS de la red HFC.</p>
            </header>
            <section id="puertos-docsis-panel" class="card module-panel" aria-labelledby="puertos-docsis-title">
                <div class="gkp-section__heading">
                    <div>
                        <h3 id="puertos-docsis-title">Estado de puertos DOCSIS</h3>
                        <p id="puertos-docsis-summary">Consultando información disponible…</p>
                    </div>
                    <button id="puertos-docsis-refresh" type="button">Actualizar</button>
                </div>
                <div id="puertos-docsis-table" class="gkp-table-wrap" hidden>
                    <table class="gkp-table">
                        <thead><tr><th>Resultado</th></tr></thead>
                        <tbody id="puertos-docsis-rows"></tbody>
                    </table>
                </div>
                <div id="puertos-docsis-status" class="module-empty" role="status" aria-live="polite">Cargando…</div>
            </section>
        </div>
        <?php require __DIR__ . '/components/footer.php'; ?>
    </main>
</div>
<script src="assets/js/sidebar.js" defer></script>
<script src="assets/js/puertos-docsis.js" defer></script>
</body>
</html>
