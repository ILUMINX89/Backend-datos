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
                <div class="gkp-toolbar__summary">
                    <strong id="gkp-summary">Consultando excepciones operacionales…</strong>
                    <span>Ordenadas para revisión por prioridad operacional</span>
                </div>
                <span id="gkp-updated" class="sr-only">Última actualización: pendiente</span>
                <button id="gkp-refresh" type="button">
                    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7"/></svg>
                    <span>Actualizar</span>
                </button>
            </div>
            <div class="gkp-panels">
            <section id="alarmas" class="gkp-panel" aria-labelledby="gkp-title" aria-busy="true">
                <div class="gkp-panel-heading">
                    <div><h2 id="gkp-title">Estado actual de red</h2><p>Caídas, saturación uplink y errores CRC activos</p></div>
                    <span class="gkp-panel-total"><strong id="gkp-count">0</strong><span>eventos</span></span>
                </div>
                <p id="gkp-status" role="status" aria-live="polite">Cargando estado de la red…</p>
                <div class="gkp-table-scroll" tabindex="0" role="region" aria-label="Estado actual de red; tabla desplazable en pantallas pequeñas">
                    <table class="gkp-table">
                        <thead><tr><th scope="col">Equipo</th><th scope="col">Puerto o interfaz</th><th scope="col">Valor</th><th scope="col">Estado</th></tr></thead>
                        <tbody id="gkp-rows"></tbody>
                    </table>
                </div>
                <p class="gkp-panel-foot"><span>Datos operacionales actuales</span><span class="gkp-scroll-hint">Desliza para ver más →</span></p>
                <noscript>Activa JavaScript para consultar el estado de la red.</noscript>
            </section>
            <section id="temperatura-panel" class="gkp-panel" aria-labelledby="temperatura-title" aria-busy="true">
                <div class="gkp-panel-heading">
                    <div><h2 id="temperatura-title">Temperatura OLT</h2><p>Solo equipos por encima de 70 °C</p></div>
                    <span class="gkp-panel-total"><strong id="temperatura-count">0</strong><span>excepciones</span></span>
                </div>
                <div class="temperature-legend" aria-label="Umbrales de temperatura">
                    <span><i class="temperature-legend__yellow"></i>70–79 °C · elevada</span>
                    <span><i class="temperature-legend__orange"></i>80–89 °C · alta</span>
                    <span><i class="temperature-legend__red"></i>≥90 °C · crítica</span>
                </div>
                <p id="temperatura-status" role="status" aria-live="polite">Cargando temperatura OLT…</p>
                <div id="temperatura-table-region" class="gkp-table-scroll" tabindex="0" role="region" aria-label="Temperatura OLT; tabla desplazable en pantallas pequeñas">
                    <table class="gkp-table">
                        <thead><tr><th scope="col">Equipo</th><th scope="col">Temperatura</th><th scope="col">Estado</th></tr></thead>
                        <tbody id="temperatura-rows"></tbody>
                    </table>
                </div>
                <div id="temperatura-empty" class="temperature-empty" hidden>
                    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 4 4L19 6"/></svg>
                    <strong>Sin equipos por encima de 70 °C</strong>
                    <span>Las lecturas actuales permanecen por debajo del umbral de excepción.</span>
                </div>
                <p class="gkp-panel-foot"><span>Escala contextual de temperatura OLT</span><span class="gkp-scroll-hint">Desliza para ver más →</span></p>
                <p id="temperatura-updated" class="sr-only">Última actualización: pendiente</p>
                <noscript>Activa JavaScript para consultar la temperatura OLT.</noscript>
            </section>
            <section id="perdida-latencia-panel" class="gkp-panel gkp-panel--full" aria-labelledby="perdida-latencia-title" aria-busy="true">
                <div class="gkp-panel-heading">
                    <div><h2 id="perdida-latencia-title">Pérdida de gestión y latencia</h2><p>Última lectura disponible por equipo en los últimos 10 minutos</p></div>
                    <span class="gkp-panel-total"><strong id="perdida-latencia-count">0</strong><span>equipos</span></span>
                </div>
                <p id="perdida-latencia-status" role="status" aria-live="polite">Cargando pérdida y latencia…</p>
                <div id="perdida-latencia-table-region" class="gkp-table-scroll" tabindex="0" role="region" aria-label="Pérdida y latencia OLT; tabla desplazable en pantallas pequeñas">
                    <table class="gkp-table">
                        <thead><tr><th scope="col">Equipo</th><th scope="col">Pérdida</th><th scope="col">Latencia</th><th scope="col">Estado</th><th scope="col">Tiempo</th></tr></thead>
                        <tbody id="perdida-latencia-rows"></tbody>
                    </table>
                </div>
                <div id="perdida-latencia-empty" class="temperature-empty" hidden>
                    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 4 4L19 6"/></svg>
                    <strong>Sin lecturas recientes</strong>
                    <span>No se encontraron muestras de latencia en los últimos 10 minutos.</span>
                </div>
                <p class="gkp-panel-foot"><span>La fuente no define unidad ni umbrales de latencia</span><span class="gkp-scroll-hint">Desliza para ver más →</span></p>
                <p id="perdida-latencia-updated" class="sr-only">Última actualización: pendiente</p>
                <noscript>Activa JavaScript para consultar pérdida y latencia OLT.</noscript>
            </section>
            </div>
        </div>
        <?php require __DIR__ . '/components/footer.php'; ?>
    </main>
</div>
<script src="assets/js/gkp.js" defer></script>
<script src="assets/js/temperatura.js" defer></script>
<script src="assets/js/perdida_latencia.js" defer></script>
</body>
</html>
