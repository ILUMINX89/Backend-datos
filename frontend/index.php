<?php declare(strict_types=1); ?>

<!doctype html>
<html lang="es">

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <title>NOC BOA | Centro de Alarmas</title>

    <link rel="stylesheet" href="assets/css/style.css">
    <link rel="stylesheet" href="assets/css/sidebar.css">
    <link rel="stylesheet" href="assets/css/header.css">
    <link rel="stylesheet" href="assets/css/index.css">
</head>

<body>

<div class="app">

    <?php require __DIR__ . '/components/sidebar.php'; ?>

    <main class="main">

        <?php require __DIR__ . '/components/header.php'; ?>


        <!-- =========================================================
             ERROR DE CONECTIVIDAD
        ========================================================== -->

        <div
            id="error-state"
            class="error-state"
            role="status"
            hidden
        >
            <span class="error-state__pulse"></span>

            <div>
                <strong>Sin comunicación con el origen de datos</strong>
                <small>
                    Reintentando conexión automáticamente…
                </small>
            </div>
        </div>


        <!-- =========================================================
             RESUMEN DE ALARMAS
        ========================================================== -->

        <section
            class="kpis wallboard-kpis"
            aria-label="Resumen de alarmas"
        >

            <article
                id="alarm-card"
                class="card wallboard-kpi alarm-card"
            >

                <div class="wallboard-kpi__label">
                    Alarmas activas
                </div>

                <div class="wallboard-kpi__content">

                    <strong
                        id="total"
                        class="kpi"
                    >
                        0
                    </strong>

                    <span class="wallboard-kpi__indicator indicator-blue"></span>

                </div>

            </article>


            <article class="card wallboard-kpi critical">

                <div class="wallboard-kpi__label">
                    Críticas
                </div>

                <div class="wallboard-kpi__content">

                    <strong
                        id="tipo1"
                        class="kpi"
                    >
                        0
                    </strong>

                    <span class="wallboard-kpi__indicator indicator-red"></span>

                </div>

            </article>


            <article class="card wallboard-kpi major">

                <div class="wallboard-kpi__label">
                    Mayores
                </div>

                <div class="wallboard-kpi__content">

                    <strong
                        id="tipo2"
                        class="kpi"
                    >
                        0
                    </strong>

                    <span class="wallboard-kpi__indicator indicator-orange"></span>

                </div>

            </article>


            <article class="card wallboard-kpi minor">

                <div class="wallboard-kpi__label">
                    Menores
                </div>

                <div class="wallboard-kpi__content">

                    <strong
                        id="tipo3"
                        class="kpi"
                    >
                        0
                    </strong>

                    <span class="wallboard-kpi__indicator indicator-yellow"></span>

                </div>

            </article>

        </section>


        <!-- =========================================================
             CENTRO PRINCIPAL DE ALARMAS
        ========================================================== -->

        <section
            id="alarmas"
            class="card alarm-monitor"
        >

            <!-- CABECERA -->

            <div class="alarm-monitor__header">

                <div class="alarm-monitor__title">

                    <div class="live-indicator">
                        <span></span>
                    </div>

                    <div>

                        <span class="section-label">
                            OPERACIÓN EN VIVO
                        </span>

                        <h2>
                            Alarmas en tiempo real
                        </h2>

                        <p>
                            Eventos activos de infraestructura GPON / OLT
                        </p>

                    </div>

                </div>


                <div class="monitor-status">

                    <span class="monitor-status__dot"></span>

                    <div>
                        <strong>Monitoreo activo</strong>
                        <small>Actualización automática</small>
                    </div>

                </div>

            </div>


            <!-- FILTROS -->

            <div class="alarm-toolbar">

                <div class="alarm-search">

                    <span class="alarm-search__icon">
                        ⌕
                    </span>

                    <input
                        id="busqueda"
                        type="search"
                        placeholder="Buscar OLT, nodo, sitio o descripción..."
                        aria-label="Buscar alarmas"
                    >

                </div>


                <select
                    id="filtro-tipo"
                    aria-label="Filtrar por tipo"
                >

                    <option value="">
                        Todas las severidades
                    </option>

                    <option value="1">
                        Críticas
                    </option>

                    <option value="2">
                        Mayores
                    </option>

                    <option value="3">
                        Menores
                    </option>

                </select>


                <select
                    id="filtro-estado"
                    aria-label="Filtrar por estado"
                >

                    <option value="">
                        Todos los estados
                    </option>

                    <option value="ACTIVA">
                        Activas
                    </option>

                    <option value="RECONOCIDA">
                        Reconocidas
                    </option>

                </select>

            </div>


            <!-- TABLA -->

            <div class="alarm-table-wrapper">

                <table id="tabla-alarmas">

                    <thead>

                    <tr>

                        <th>Hora</th>

                        <th>Severidad</th>

                        <th>Estado</th>

                        <th>OLT</th>

                        <th>Puerto</th>

                        <th>Nodo / Sitio</th>

                        <th>Descripción</th>

                        <th>Valor</th>

                        <th>Acciones</th>

                    </tr>

                    </thead>


                    <tbody></tbody>

                </table>


                <!-- ESTADO SIN ALARMAS -->

                <div
                    id="alarmas-vacias"
                    class="alarm-empty"
                >

                    <div class="alarm-empty__icon">
                        ✓
                    </div>

                    <strong>
                        Sin alarmas activas
                    </strong>

                    <span>
                        La infraestructura no registra eventos pendientes.
                    </span>

                </div>

            </div>

        </section>


        <?php require __DIR__ . '/components/footer.php'; ?>

    </main>

</div>


<!-- =============================================================
     ALERTA DE NUEVO EVENTO
============================================================== -->

<aside
    id="alarm-toast"
    class="toast critical-toast"
    role="alert"
    hidden
>

    <div class="critical-toast__signal">
        !
    </div>


    <div class="critical-toast__content">

        <span>
            NUEVA ALARMA CRÍTICA
        </span>

        <strong>
            Evento crítico detectado
        </strong>

        <small>
            Se ha registrado una nueva afectación que requiere revisión.
        </small>

    </div>


    <button
        id="cerrar-alerta"
        type="button"
    >
        Cerrar
    </button>

</aside>


<script src="assets/js/tablas.js" defer></script>
<script src="assets/js/alarmas.js" defer></script>
<script src="assets/js/app.js" defer></script>

</body>

</html>