<?php declare(strict_types=1); ?>
<!doctype html>
<html lang="es">

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <title>RKP | Intermitencias y puertos duplicados</title>

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
                    <h2>Intermitencias y puertos duplicados</h2>

                    <p>
                        Seguimiento de intermitencias y nodos asociados a múltiples puertos CMTS.
                    </p>
                </header>

                <div class="intermitencias-grid">
                    <section id="intermitencias-panel" class="card module-panel" aria-labelledby="intermitencias-title">

                    <div class="gkp-section__heading">

                        <div>
                            <h3 id="intermitencias-title">
                                Intermitencias
                            </h3>

                            <p id="intermitencias-summary">
                                Consultando información disponible…
                            </p>
                        </div>

                        <button id="intermitencias-refresh" type="button">
                            Actualizar
                        </button>

                    </div>

                    <div id="intermitencias-table" class="gkp-table-wrap" hidden>
                        <table class="gkp-table">

                            <thead>
                                <tr>
                                    <th>CMTS</th>
                                    <th>Puerto</th>
                                    <th>Nodo</th>
                                    <th>Intermitencias</th>
                                    <th>Estado</th>
                                </tr>
                            </thead>

                            <tbody id="intermitencias-rows">
                            </tbody>

                        </table>
                    </div>

                    <div id="intermitencias-status" class="module-empty" role="status" aria-live="polite">
                        Cargando…
                    </div>

                    </section>

                    <section id="duplicados-panel" class="card module-panel" aria-labelledby="duplicados-title">
                        <div class="gkp-section__heading">
                            <div>
                                <h3 id="duplicados-title">Puertos duplicados</h3>
                                <p id="duplicados-summary">Consultando información disponible…</p>
                            </div>

                            <button id="duplicados-refresh" type="button">Actualizar</button>
                        </div>

                        <div id="duplicados-table" class="gkp-table-wrap" hidden>
                            <table class="gkp-table">
                                <thead>
                                    <tr>
                                        <th>Nodo</th>
                                        <th>Ubicaciones</th>
                                        <th>CMTS</th>
                                        <th>Puerto</th>
                                    </tr>
                                </thead>
                                <tbody id="duplicados-rows"></tbody>
                            </table>
                        </div>

                        <div id="duplicados-status" class="module-empty" role="status" aria-live="polite">
                            Cargando…
                        </div>
                    </section>
                </div>

            </div>

            <?php require __DIR__ . '/components/footer.php'; ?>

        </main>

    </div>

    <script src="assets/js/sidebar.js" defer></script>
    <script src="assets/js/intermitencias.js" defer></script>

</body>

</html>
