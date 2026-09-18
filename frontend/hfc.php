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

<body class="gkp-page hfc-page">
    <div class="app">
        <?php require __DIR__ . '/components/sidebar.php'; ?>
        <main class="main">
            <?php require __DIR__ . '/components/header.php'; ?>
            <div class="module-content">
                <header class="module-heading">
                    <h2>Vista general HFC</h2>
                    <p>Afectaciones por utilización o degradación de señal.</p>
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
                                <tr>
                                    <th>CMTS</th>
                                    <th>Nodo / puerto</th>
                                    <th>Utilización promedio</th>
                                    <th>Estado</th>
                                </tr>
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
    <div id="hfc-modal" class="hfc-modal" hidden>
        <div class="hfc-modal__backdrop" data-modal-close></div>
        <section class="hfc-dialog" role="dialog" aria-modal="true" aria-labelledby="hfc-modal-title" tabindex="-1">
            <header class="hfc-dialog__header">
                <div>
                    <h2 id="hfc-modal-title">Detalle de saturación</h2>
                    <p id="hfc-modal-cmts"></p>
                </div>
                <button id="hfc-modal-close" class="hfc-icon-button" type="button" aria-label="Cerrar detalle"
                    title="Cerrar">
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M6 6l12 12M18 6L6 18" />
                    </svg>
                </button>
            </header>
            <div class="hfc-dialog__body">
                <div class="hfc-chart-column">
                    <div class="hfc-selected">
                        <div><span>Nodo seleccionado</span><strong id="hfc-modal-node"></strong></div>
                        <div><span>Estado</span><strong id="hfc-modal-state"></strong></div>
                        <div><span>Utilización promedio</span><strong id="hfc-modal-value"></strong></div>
                    </div>
                    <div class="hfc-chart-heading">
                        <div>
                            <h3 id="hfc-chart-title">Gráfica últimos 3 días</h3>
                            <span>Grafana · actualización según origen</span>
                        </div>

                        <div class="hfc-chart-switch hfc-range" aria-label="Tipo de gráfica">
                            <button type="button" data-panel="panel-1" class="is-active">
                                Tráfico
                            </button>

                            <button type="button" data-panel="panel-7">
                                SNR UP
                            </button>
                        </div>

                        <div class="hfc-time-range hfc-range" aria-label="Rango de tiempo">
                            <button type="button" data-days="1">1D</button>
                            <button type="button" data-days="3" class="is-active">3D</button>
                            <button type="button" data-days="7">7D</button>
                            <button type="button" data-days="30">30D</button>
                        </div>
                    </div>
                    <div class="hfc-chart-frame">
                        <iframe id="hfc-grafana" loading="lazy" title="Gráfica Grafana del nodo seleccionado"></iframe>
                    </div>
                </div>
                <aside class="hfc-related" aria-labelledby="hfc-related-title">
                    <h3 id="hfc-related-title">Otros puertos afectados del mismo CMTS</h3>
                    <section id="hfc-use-group" class="hfc-port-group">
                        <h4>Saturación por uso</h4>
                        <div id="hfc-use-list" class="hfc-port-list"></div>
                    </section>
                    <section id="hfc-degradation-group" class="hfc-port-group">
                        <h4>Saturación por degradación</h4>
                        <div id="hfc-degradation-list" class="hfc-port-list"></div>
                    </section>
                </aside>
            </div>
        </section>
    </div>
    <script src="assets/js/sidebar.js" defer></script>
    <script src="assets/js/hfc.js" defer></script>
</body>

</html>