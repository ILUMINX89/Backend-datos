<?php declare(strict_types=1); ?>
<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>NOC BOA</title>
    <link rel="stylesheet" href="assets/css/style.css">
</head>
<body>
<div class="app">
    <?php require __DIR__ . '/components/sidebar.php'; ?>
    <main class="main">
        <?php require __DIR__ . '/components/header.php'; ?>
        <div id="error-state" class="error-state" role="status" hidden>Datos temporalmente no disponibles</div>

        <section class="kpis" aria-label="Resumen de alarmas">
            <article id="alarm-card" class="card alarm-card">
                <h2>🔔 Alarmas Activas</h2><strong id="total" class="kpi">0</strong>
            </article>
            <article class="card critical"><h2>Tipo 1 · Críticas</h2><strong id="tipo1" class="kpi">0</strong></article>
            <article class="card major"><h2>Tipo 2 · Mayores</h2><strong id="tipo2" class="kpi">0</strong></article>
            <article class="card minor"><h2>Tipo 3 · Menores</h2><strong id="tipo3" class="kpi">0</strong></article>
        </section>

        <section class="panels">
            <article class="card"><h2>Tendencia (24h)</h2><div id="tendencia" class="chart-placeholder">Esperando datos…</div></article>
            <article class="card"><h2>Top equipos con alarmas</h2><ol id="top-list" class="top-list"></ol></article>
        </section>

        <section id="alarmas" class="card table-card">
            <div class="table-head">
                <h2>Alarmas en tiempo real</h2>
                <input id="busqueda" type="search" placeholder="Buscar por OLT, nodo o descripción" aria-label="Buscar alarmas">
                <select id="filtro-tipo" aria-label="Filtrar por tipo">
                    <option value="">Todos los tipos</option><option value="1">Tipo 1</option><option value="2">Tipo 2</option><option value="3">Tipo 3</option>
                </select>
                <select id="filtro-estado" aria-label="Filtrar por estado"><option value="">Todos los estados</option><option value="ACTIVA">Activa</option><option value="RECONOCIDA">Reconocida</option></select>
            </div>
            <div class="scroll"><table id="tabla-alarmas"><thead><tr><th>Fecha / Hora</th><th>Tipo</th><th>Estado</th><th>OLT</th><th>Puerto</th><th>Descripción</th><th>Nodo / Sitio</th><th>Valor</th><th>Acciones</th></tr></thead><tbody></tbody></table></div>
        </section>
        <?php require __DIR__ . '/components/footer.php'; ?>
    </main>
</div>
<aside id="alarm-toast" class="toast" role="alert" hidden><span>🔔</span><div><strong>Nueva alarma crítica</strong><small>El aviso se detiene al interactuar; la alarma permanece visible.</small></div><button id="cerrar-alerta" type="button">Cerrar</button></aside>
<script src="assets/js/tablas.js" defer></script>
<script src="assets/js/alarmas.js" defer></script>
<script src="assets/js/app.js" defer></script>
</body>
</html>
