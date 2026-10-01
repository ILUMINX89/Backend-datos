<?php declare(strict_types=1); ?>
<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>RKP | Recursos ZTE</title>
    <link rel="stylesheet" href="assets/css/style.css">
    <link rel="stylesheet" href="assets/css/sidebar.css">
    <link rel="stylesheet" href="assets/css/gkp.css">
    <link rel="stylesheet" href="assets/css/module-page.css">
</head>
<body class="gkp-page hfc-page">
<div class="app">
    <?php require __DIR__ . '/components/sidebar.php'; ?>
    <main class="main">
        <?php $headerTitle = 'Recursos ZTE'; $headerDescription = 'Disponibilidad de licencias y recursos con atención prioritaria.'; ?>
        <?php require __DIR__ . '/components/header.php'; ?>
        <div class="module-content">
            <header class="module-heading">
                <h2>Recursos ZTE</h2>
                <p>Licencias y recursos ZTE con menos del 15% de capacidad disponible.</p>
            </header>
            <section id="recursos-zte-panel" class="card module-panel" aria-labelledby="recursos-zte-title" aria-busy="true">
                <div class="gkp-section__heading">
                    <div>
                        <h3 id="recursos-zte-title">Licencias con baja disponibilidad</h3>
                        <p id="recursos-zte-summary">Consultando disponibilidad…</p>
                    </div>
                    <button id="recursos-zte-refresh" type="button">Actualizar</button>
                </div>
                <div id="recursos-zte-table" class="gkp-table-wrap" hidden tabindex="0" role="region" aria-label="Licencias ZTE con baja disponibilidad; tabla desplazable">
                    <table class="gkp-table">
                        <thead><tr><th scope="col">OLT</th><th scope="col">Recurso</th><th scope="col">Usado</th><th scope="col">Disponible</th><th scope="col">Total</th><th scope="col">Disponible %</th><th scope="col">Actualizado</th></tr></thead>
                        <tbody id="recursos-zte-rows"></tbody>
                    </table>
                </div>
                <div id="recursos-zte-status" class="module-empty" role="status" aria-live="polite">Cargando…</div>
            </section>
        </div>
        <?php require __DIR__ . '/components/footer.php'; ?>
    </main>
</div>
<script src="assets/js/sidebar.js" defer></script>
<script src="assets/js/recursos-zte.js" defer></script>
</body>
</html>
