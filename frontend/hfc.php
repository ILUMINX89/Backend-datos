<?php declare(strict_types=1); ?>
<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>RKP | Vista general HFC</title>
    <link rel="stylesheet" href="assets/css/style.css">
    <link rel="stylesheet" href="assets/css/sidebar.css">
    <link rel="stylesheet" href="assets/css/gkp.css">
    <link rel="stylesheet" href="assets/css/module-page.css">
</head>
<body class="gkp-page">
<div class="app">
    <?php require __DIR__ . '/components/sidebar.php'; ?>
    <main class="main">
        <?php require __DIR__ . '/components/header.php'; ?>
        <div class="module-content">
            <header class="module-heading">
                <h2>Vista general HFC</h2>
                <p>Puertos CMTS cuya utilización actual supera el 80%.</p>
            </header>
            <section class="card module-panel" id="alarmas" aria-labelledby="hfc-title">
                <div class="gkp-section__heading">
                    <div>
                        <h3 id="hfc-title">Excepciones HFC</h3>
                        <p id="hfc-summary">Consultando saturaciones CMTS…</p>
                    </div>
                    <button id="hfc-refresh" type="button">Actualizar</button>
                </div>
                <div id="hfc-table" class="gkp-table-wrap">
                    <table class="gkp-table">
                        <thead>
                            <tr><th>CMTS</th><th>Nodo / puerto</th><th>Utilización</th><th>Estado</th></tr>
                        </thead>
                        <tbody id="hfc-rows"></tbody>
                    </table>
                </div>
                <div id="hfc-status" class="module-empty" role="status" aria-live="polite"></div>
            </section>
        </div>
        <?php require __DIR__ . '/components/footer.php'; ?>
    </main>
</div>
<script src="assets/js/sidebar.js" defer></script>
<script src="assets/js/hfc.js" defer></script>
</body>
</html>
