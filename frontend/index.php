<?php declare(strict_types=1); ?>
<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>GKP | Estado actual de red</title>
    <link rel="stylesheet" href="assets/css/style.css">
    <link rel="stylesheet" href="assets/css/sidebar.css">
    <link rel="stylesheet" href="assets/css/gkp.css">
</head>
<body class="gkp-page">
<div class="app">
    <?php require __DIR__ . '/components/sidebar.php'; ?>
    <main class="main">
        <?php require __DIR__ . '/components/header.php'; ?>
        <div class="gkp-content">
            <div class="gkp-toolbar">
                <span id="gkp-updated">Última actualización: pendiente</span>
                <button id="gkp-refresh" type="button">↻ Actualizar</button>
            </div>
            <div class="gkp-panels">
            <section id="alarmas" class="gkp-panel" aria-labelledby="gkp-title" aria-busy="true">
                <div class="gkp-panel-heading">
                    <div class="gkp-bars" aria-hidden="true"><i></i><i></i><i></i></div>
                    <div><h2 id="gkp-title">Estado actual de red</h2><p>Eventos y métricas relevantes</p></div>
                </div>
                <p class="gkp-context">Caídas actuales · CRC y saturación: episodios de las últimas 24 horas</p>
                <p id="gkp-status" role="status" aria-live="polite">Cargando estado de la red…</p>
                <div class="gkp-table-scroll" tabindex="0" role="region" aria-label="Estado actual de red">
                    <table class="gkp-table">
                        <thead><tr><th scope="col">Equipo</th><th scope="col">Puerto o interfaz</th><th scope="col">Valor</th><th scope="col">Estado</th></tr></thead>
                        <tbody id="gkp-rows"></tbody>
                    </table>
                </div>
                <noscript>Activa JavaScript para consultar el estado de la red.</noscript>
            </section>
            <section id="temperatura-panel" class="gkp-panel" aria-labelledby="temperatura-title" aria-busy="true">
                <div class="gkp-panel-heading">
                    <div><h2 id="temperatura-title">Temperatura OLT</h2><p>Lecturas actuales por tarjeta</p></div>
                </div>
                <p class="gkp-context">Últimos 10 minutos · Estado provisional: Normal; umbrales pendientes de confirmar.</p>
                <p id="temperatura-status" role="status" aria-live="polite">Cargando temperatura OLT…</p>
                <div class="gkp-table-scroll" tabindex="0" role="region" aria-label="Temperatura OLT">
                    <table class="gkp-table">
                        <thead><tr><th scope="col">Equipo</th><th scope="col">Zona</th><th scope="col">Temperatura</th><th scope="col">Estado</th></tr></thead>
                        <tbody id="temperatura-rows"></tbody>
                    </table>
                </div>
                <p id="temperatura-updated" class="gkp-context">Última actualización: pendiente</p>
                <noscript>Activa JavaScript para consultar la temperatura OLT.</noscript>
            </section>
            </div>
        </div>
        <?php require __DIR__ . '/components/footer.php'; ?>
    </main>
</div>
<script src="assets/js/gkp.js" defer></script>
<script src="assets/js/temperatura.js" defer></script>
</body>
</html>
