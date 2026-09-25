<?php declare(strict_types=1); ?>
<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>RKP | Agotamiento IP e intermitencias</title>
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
                    <h2>Agotamiento IP e intermitencias</h2>
                    <p>Seguimiento de disponibilidad de direcciones IP e intermitencias detectadas en puertos FTTH.</p>
                </header>
                <div class="intermitencias-grid">
                    <section class="card module-panel" aria-labelledby="agotamiento-ip-title">
                        <div class="gkp-section__heading">
                            <div><h3 id="agotamiento-ip-title">Agotamiento IP</h3></div>
                        </div>
                        <div class="module-empty" role="status">
                            La fuente de datos de agotamiento IP aún no está conectada.
                        </div>
                    </section>
                    <section id="intermitencias-ftth-panel" class="card module-panel" aria-labelledby="intermitencias-ftth-title">
                        <div class="gkp-section__heading">
                            <div>
                                <h3 id="intermitencias-ftth-title">Intermitencias FTTH</h3>
                                <p id="intermitencias-ftth-summary">Consultando información disponible…</p>
                            </div>
                            <button id="intermitencias-ftth-refresh" type="button">Actualizar</button>
                        </div>
                        <div id="intermitencias-ftth-table" class="gkp-table-wrap" hidden>
                            <table class="gkp-table">
                                <thead>
                                    <tr>
                                        <th>OLT</th>
                                        <th>Puerto</th>
                                        <th>Día</th>
                                        <th>Caídas</th>
                                        <th>Tiempo caído</th>
                                    </tr>
                                </thead>
                                <tbody id="intermitencias-ftth-rows"></tbody>
                            </table>
                        </div>
                        <div id="intermitencias-ftth-status" class="module-empty" role="status" aria-live="polite">Cargando…</div>
                    </section>
                </div>
            </div>
            <?php require __DIR__ . '/components/footer.php'; ?>
        </main>
    </div>
    <script src="assets/js/sidebar.js" defer></script>
    <script src="assets/js/agotamiento-ip.js" defer></script>
</body>
</html>
