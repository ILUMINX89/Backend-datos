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
                    <span class="gkp-toolbar__separator" aria-hidden="true">·</span>
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
            <div class="gkp-secondary-panels">
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
                        <thead><tr><th scope="col">Equipo</th><th scope="col">Temperatura</th></tr></thead>
                        <tbody id="temperatura-rows"></tbody>
                    </table>
                </div>
                <div id="temperatura-empty" class="panel-ok-state" hidden>
                    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 4 4L19 6"/></svg>
                    <span class="sr-only">Sin excepciones de temperatura OLT</span>
                </div>
                <p class="gkp-panel-foot"><span>Escala contextual de temperatura OLT</span><span class="gkp-scroll-hint">Desliza para ver más →</span></p>
                <p id="temperatura-updated" class="sr-only">Última actualización: pendiente</p>
                <noscript>Activa JavaScript para consultar la temperatura OLT.</noscript>
            </section>
            <section id="perdida-latencia-panel" class="gkp-panel" aria-labelledby="perdida-latencia-title" aria-busy="true">
                <div class="gkp-panel-heading">
                    <div><h2 id="perdida-latencia-title">Pérdida de gestión y latencia</h2><p>Última lectura disponible por equipo en los últimos 10 minutos</p></div>
                    <span class="gkp-panel-total"><strong id="perdida-latencia-count">0</strong><span>eventos</span></span>
                </div>
                <p id="perdida-latencia-status" role="status" aria-live="polite">Cargando pérdida y latencia…</p>
                <div id="perdida-latencia-table-region" class="gkp-table-scroll" tabindex="0" role="region" aria-label="Pérdida y latencia OLT; tabla desplazable en pantallas pequeñas">
                    <table class="gkp-table">
                        <thead><tr><th scope="col">Equipo</th><th scope="col">Valor</th><th scope="col">Estado</th></tr></thead>
                        <tbody id="perdida-latencia-rows"></tbody>
                    </table>
                </div>
                <div id="perdida-latencia-empty" class="panel-ok-state" hidden>
                    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 4 4L19 6"/></svg>
                    <span class="sr-only">Sin excepciones de pérdida o latencia</span>
                </div>
                <p class="gkp-panel-foot"><span>Solo pérdida &gt; 10% y latencia &gt; 50 ms</span><span class="gkp-scroll-hint">Desliza para ver más →</span></p>
                <p id="perdida-latencia-updated" class="sr-only">Última actualización: pendiente</p>
                <noscript>Activa JavaScript para consultar pérdida y latencia OLT.</noscript>
            </section>
            </div>
            </div>
        </div>
        <?php require __DIR__ . '/components/footer.php'; ?>
    </main>
</div>
<div id="ftth-modal" class="ftth-modal" hidden>
    <div class="ftth-modal__backdrop" data-ftth-close aria-hidden="true"></div>
    <section class="ftth-dialog" role="dialog" aria-modal="true" aria-labelledby="ftth-modal-title" tabindex="-1">
        <header class="ftth-dialog__header">
            <div>
                <h2 id="ftth-modal-title">Detalle OLT</h2>
                <p id="ftth-modal-olt"></p>
            </div>
            <button id="ftth-modal-close" class="ftth-close" type="button" aria-label="Cerrar detalle OLT" title="Cerrar">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"/></svg>
            </button>
        </header>
        <div class="ftth-dialog__body">
            <div class="ftth-controls">
                <div class="ftth-range" role="group" aria-label="Rango de tiempo">
                    <button type="button" data-ftth-days="1" class="is-active" aria-pressed="true">1D</button>
                    <button type="button" data-ftth-days="3" aria-pressed="false">3D</button>
                    <button type="button" data-ftth-days="7" aria-pressed="false">7D</button>
                    <button type="button" data-ftth-days="30" aria-pressed="false">30D</button>
                </div>
                <div class="ftth-panel-toggles" role="group" aria-label="Gráficas adicionales">
                    <button id="ftth-toggle-power" type="button" aria-pressed="false">Potencias uplink</button>
                    <button id="ftth-toggle-crc" type="button" aria-pressed="false">Errores CRC</button>
                </div>
            </div>
            <div class="ftth-charts">
                <article class="ftth-chart-card">
                    <h3>Tráfico OLT</h3>
                    <div class="ftth-chart-frame">
                        <span class="ftth-loading" aria-live="polite">Cargando gráfica…</span>
                        <iframe id="ftth-grafana-main" title="Tráfico OLT" loading="eager"></iframe>
                    </div>
                </article>
                <article id="ftth-power-card" class="ftth-chart-card" hidden>
                    <h3>Potencias uplink</h3>
                    <div class="ftth-chart-frame">
                        <span class="ftth-loading" aria-live="polite">Cargando gráfica…</span>
                        <iframe id="ftth-grafana-power" title="Potencias de puertos uplink" loading="lazy"></iframe>
                    </div>
                </article>
                <article id="ftth-crc-card" class="ftth-chart-card" hidden>
                    <h3>Errores CRC</h3>
                    <div class="ftth-chart-frame">
                        <span class="ftth-loading" aria-live="polite">Cargando gráfica…</span>
                        <iframe id="ftth-grafana-crc" title="Errores CRC" loading="lazy"></iframe>
                    </div>
                </article>
            </div>
        </div>
    </section>
</div>
<script src="assets/js/sidebar.js" defer></script>
<script src="assets/js/gkp.js" defer></script>
<script src="assets/js/temperatura.js" defer></script>
<script src="assets/js/perdida_latencia.js" defer></script>
</body>
</html>
