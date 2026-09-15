<?php declare(strict_types=1); ?>

<!doctype html>
<html lang="es">

<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <title>NOC BOA | Reportes</title>

    <link rel="stylesheet" href="assets/css/style.css">
    <link rel="stylesheet" href="assets/css/sidebar.css">
    <link rel="stylesheet" href="assets/css/header.css">
    <link rel="stylesheet" href="assets/css/reportes.css">
</head>

<body>

<div class="app">

    <?php require __DIR__ . '/components/sidebar.php'; ?>

    <main class="main">

        <?php require __DIR__ . '/components/header.php'; ?>


        <!-- =========================================================
             HEADER ADMINISTRATIVO
        ========================================================== -->

        <section class="reports-heading">

            <div>

                <span class="section-label">
                    ANALÍTICA OPERACIONAL
                </span>

                <h2>
                    Reportes y comportamiento de alarmas
                </h2>

                <p>
                    Análisis histórico y consolidado de eventos registrados
                    en la infraestructura GPON / OLT.
                </p>

            </div>

        </section>


        <!-- =========================================================
             FILTROS
        ========================================================== -->

        <section class="card reports-filters">

            <div class="reports-filter-group">

                <label for="fecha-desde">
                    Desde
                </label>

                <input
                    id="fecha-desde"
                    type="date"
                >

            </div>


            <div class="reports-filter-group">

                <label for="fecha-hasta">
                    Hasta
                </label>

                <input
                    id="fecha-hasta"
                    type="date"
                >

            </div>


            <div class="reports-filter-group">

                <label for="reporte-severidad">
                    Severidad
                </label>

                <select id="reporte-severidad">

                    <option value="">
                        Todas
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

            </div>


            <button
                id="aplicar-filtros"
                class="reports-filter-button"
                type="button"
            >
                Aplicar filtros
            </button>

        </section>


        <!-- =========================================================
             RESUMEN
        ========================================================== -->

        <section class="reports-kpis">

            <article class="card reports-kpi">

                <span>
                    Total de eventos
                </span>

                <strong id="reporte-total">
                    0
                </strong>

            </article>


            <article class="card reports-kpi reports-kpi--critical">

                <span>
                    Críticas
                </span>

                <strong id="reporte-criticas">
                    0
                </strong>

            </article>


            <article class="card reports-kpi reports-kpi--major">

                <span>
                    Mayores
                </span>

                <strong id="reporte-mayores">
                    0
                </strong>

            </article>


            <article class="card reports-kpi reports-kpi--minor">

                <span>
                    Menores
                </span>

                <strong id="reporte-menores">
                    0
                </strong>

            </article>

        </section>


        <!-- =========================================================
             GRAFICAS PRINCIPALES
        ========================================================== -->

        <section class="reports-grid reports-grid--main">


            <!-- TENDENCIA -->

            <article class="card report-card">

                <div class="report-card__header">

                    <div>

                        <span class="section-label">
                            HISTÓRICO
                        </span>

                        <h2>
                            Tendencia de alarmas
                        </h2>

                        <p>
                            Evolución de eventos durante el período seleccionado.
                        </p>

                    </div>

                </div>


                <div
                    id="grafica-tendencia"
                    class="report-chart"
                >

                    <div class="chart-empty">

                        <span class="chart-empty__pulse"></span>

                        <strong>
                            Esperando información
                        </strong>

                        <small>
                            La gráfica se generará con los datos disponibles.
                        </small>

                    </div>

                </div>

            </article>


            <!-- DISTRIBUCION -->

            <article class="card report-card">

                <div class="report-card__header">

                    <div>

                        <span class="section-label">
                            SEVERIDAD
                        </span>

                        <h2>
                            Distribución de alarmas
                        </h2>

                        <p>
                            Participación de cada nivel de severidad.
                        </p>

                    </div>

                </div>


                <div
                    id="grafica-severidad"
                    class="report-chart report-chart--small"
                >

                    <div class="chart-empty">

                        <strong>
                            Sin datos disponibles
                        </strong>

                    </div>

                </div>

            </article>

        </section>


        <!-- =========================================================
             SEGUNDA FILA
        ========================================================== -->

        <section class="reports-grid">


            <!-- TOP EQUIPOS -->

            <article class="card report-card">

                <div class="report-card__header">

                    <div>

                        <span class="section-label">
                            INFRAESTRUCTURA
                        </span>

                        <h2>
                            Equipos con mayor afectación
                        </h2>

                        <p>
                            OLT con mayor cantidad de eventos registrados.
                        </p>

                    </div>

                </div>


                <div
                    id="grafica-top-equipos"
                    class="report-chart"
                >
                    Esperando datos…
                </div>

            </article>


            <!-- TOP NODOS -->

            <article class="card report-card">

                <div class="report-card__header">

                    <div>

                        <span class="section-label">
                            NODOS
                        </span>

                        <h2>
                            Sitios con mayor recurrencia
                        </h2>

                        <p>
                            Nodos o sitios con mayor número de alarmas.
                        </p>

                    </div>

                </div>


                <ol
                    id="reporte-top-nodos"
                    class="report-ranking"
                ></ol>

            </article>

        </section>


        <!-- =========================================================
             ACTIVAS VS RECONOCIDAS
        ========================================================== -->

        <section class="reports-grid">


            <article class="card report-card">

                <div class="report-card__header">

                    <div>

                        <span class="section-label">
                            ESTADOS
                        </span>

                        <h2>
                            Estado de las alarmas
                        </h2>

                        <p>
                            Comparación entre alarmas activas y reconocidas.
                        </p>

                    </div>

                </div>


                <div
                    id="grafica-estados"
                    class="report-chart"
                >
                    Esperando datos…
                </div>

            </article>


            <!-- RESUMEN ADMINISTRATIVO -->

            <article class="card report-card">

                <div class="report-card__header">

                    <div>

                        <span class="section-label">
                            RESUMEN
                        </span>

                        <h2>
                            Indicadores operativos
                        </h2>

                    </div>

                </div>


                <div class="report-summary">

                    <div>

                        <span>
                            OLT afectadas
                        </span>

                        <strong id="olt-afectadas">
                            0
                        </strong>

                    </div>


                    <div>

                        <span>
                            Nodos afectados
                        </span>

                        <strong id="nodos-afectados">
                            0
                        </strong>

                    </div>


                    <div>

                        <span>
                            Alarmas reconocidas
                        </span>

                        <strong id="alarmas-reconocidas">
                            0
                        </strong>

                    </div>


                    <div>

                        <span>
                            Alarmas activas
                        </span>

                        <strong id="alarmas-activas-reporte">
                            0
                        </strong>

                    </div>

                </div>

            </article>

        </section>


        <?php require __DIR__ . '/components/footer.php'; ?>

    </main>

</div>


<script src="assets/js/reportes.js" defer></script>
<script src="assets/js/app.js" defer></script>

</body>

</html>