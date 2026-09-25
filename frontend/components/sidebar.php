<?php

$sidebarPage = basename($_SERVER['PHP_SELF'] ?? 'index.php');

$overviewActive = $sidebarPage === 'index.php';

$routinePages = [
    'recursos-zte.php' => 'Recursos ZTE',
    'autofind-hw.php' => 'Autofind HW',
    'onts.php' => 'ONTs',
    'troncales-pon.php' => 'Troncales PON',
    'agotamiento-ip.php' => 'Agotamiento de IP',
];

$routinesActive = array_key_exists(
    $sidebarPage,
    $routinePages
);

$hfcRoutinePages = [
    'puertos-docsis.php' => 'Puertos DOCSIS',
    'intermitencias.php' => 'Intermitencias y puertos duplicados',
];

$hfcRoutinesActive = array_key_exists(
    $sidebarPage,
    $hfcRoutinePages
);

?>

<aside id="main-sidebar" class="sidebar" aria-label="Navegación principal">

    <!-- ======================================================
         CABECERA
         ====================================================== -->

    <div class="sidebar__top">

        <a href="index.php" class="sidebar-brand">

            <div class="sidebar-brand__icon" aria-hidden="true">
                <span class="brand-signal brand-signal--1"></span>
                <span class="brand-signal brand-signal--2"></span>
                <span class="brand-signal brand-signal--3"></span>
                <span class="brand-signal__core"></span>
            </div>

            <div class="sidebar-brand__text">
                <strong>RKP</strong>
                <span>Operación FTTH / HFC</span>
            </div>

        </a>

    </div>


    <!-- ======================================================
         NAVEGACIÓN
         ESTA PARTE TIENE SCROLL
         ====================================================== -->

    <nav class="nav" aria-label="Módulos">

        <!-- OPERACIÓN -->

        <span class="nav__section">
            Operación
        </span>

        <a class="nav__item<?= $overviewActive ? ' active' : '' ?>" href="index.php" <?= $overviewActive ? ' aria-current="page"' : '' ?>>

            <span class="nav__icon">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M3 10.5 12 3l9 7.5v9a1.5 1.5 0 0 1-1.5 1.5H15v-6H9v6H4.5A1.5 1.5 0 0 1 3 19.5z" />
                </svg>
            </span>

            <span class="nav__text">
                Vista general
            </span>

        </a>


        <!-- ==================================================
             FTTH
             ================================================== -->

        <span class="nav__section nav__section--ftth">
            FTTH
        </span>

        <div class="nav__group<?= $routinesActive ? ' is-active' : '' ?>" data-nav-group="rutinas">

            <button class="nav__item nav__toggle" type="button"
                aria-expanded="<?= $routinesActive ? 'true' : 'false' ?>" aria-controls="submenu-rutinas-ftth">

                <span class="nav__icon">
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M5 7h14M5 12h14M5 17h14M8 4v6M16 9v6M11 14v6" />
                    </svg>
                </span>

                <span class="nav__text">
                    Rutinas
                </span>

                <svg class="nav__chevron" viewBox="0 0 16 16" aria-hidden="true">
                    <path d="m4 6 4 4 4-4" />
                </svg>

            </button>


            <div id="submenu-rutinas-ftth" class="nav__submenu" <?= $routinesActive ? '' : ' hidden' ?>>

                <?php foreach ($routinePages as $page => $label): ?>

                    <a class="nav__subitem<?= $sidebarPage === $page ? ' active' : '' ?>" href="<?= htmlspecialchars(
                                $page,
                                ENT_QUOTES,
                                'UTF-8'
                            ) ?>" <?= $sidebarPage === $page
                                 ? ' aria-current="page"'
                                 : ''
                                 ?>>
                        <?= htmlspecialchars(
                            $label,
                            ENT_QUOTES,
                            'UTF-8'
                        ) ?>
                    </a>

                <?php endforeach; ?>

            </div>

        </div>


        <!-- ==================================================
             HFC
             ================================================== -->

        <span class="nav__section nav__section--secondary">
            HFC
        </span>

        <a class="nav__item<?= $sidebarPage === 'hfc.php' ? ' active' : '' ?>" href="hfc.php"
            <?= $sidebarPage === 'hfc.php'
                ? ' aria-current="page"'
                : ''
                ?>>

            <span class="nav__icon">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M4 12h4l2-5 4 10 2-5h4M4 5v14M20 5v14" />
                </svg>
            </span>

            <span class="nav__text">
                Vista general
            </span>

        </a>


        <div class="nav__group<?= $hfcRoutinesActive ? ' is-active' : '' ?>" data-nav-group="rutinas-hfc">

            <button class="nav__item nav__toggle" type="button"
                aria-expanded="<?= $hfcRoutinesActive ? 'true' : 'false' ?>" aria-controls="submenu-rutinas-hfc">

                <span class="nav__icon">
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                        <path d="M5 7h14M5 12h14M5 17h14M8 4v6M16 9v6M11 14v6" />
                    </svg>
                </span>

                <span class="nav__text">
                    Rutinas
                </span>

                <svg class="nav__chevron" viewBox="0 0 16 16" aria-hidden="true">
                    <path d="m4 6 4 4 4-4" />
                </svg>

            </button>


            <div id="submenu-rutinas-hfc" class="nav__submenu" <?= $hfcRoutinesActive ? '' : ' hidden' ?>>

                <?php foreach ($hfcRoutinePages as $page => $label): ?>

                    <a class="nav__subitem<?= $sidebarPage === $page ? ' active' : '' ?>" href="<?= htmlspecialchars(
                                $page,
                                ENT_QUOTES,
                                'UTF-8'
                            ) ?>" <?= $sidebarPage === $page
                                 ? ' aria-current="page"'
                                 : ''
                                 ?>>
                        <?= htmlspecialchars(
                            $label,
                            ENT_QUOTES,
                            'UTF-8'
                        ) ?>
                    </a>

                <?php endforeach; ?>

            </div>

        </div>


        <!-- ==================================================
             GESTIÓN
             ================================================== -->

        <span class="nav__section nav__section--secondary">
            Gestión
        </span>


        <a class="nav__item<?= $sidebarPage === 'reportes.php' ? ' active' : '' ?>" href="reportes.php"
            <?= $sidebarPage === 'reportes.php'
                ? ' aria-current="page"'
                : ''
                ?>>

            <span class="nav__icon">
                <svg viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M4 19V9m6 10V5m6 14v-7m4 7H2" />
                </svg>
            </span>

            <span class="nav__text">
                Reportes
            </span>

        </a>


        <a class="nav__item<?= $sidebarPage === 'configuracion.php' ? ' active' : '' ?>" href="configuracion.php"
            <?= $sidebarPage === 'configuracion.php'
                ? ' aria-current="page"'
                : ''
                ?>>

            <span class="nav__icon">
                <svg viewBox="0 0 24 24" aria-hidden="true">

                    <path d="M12 15.5A3.5 3.5 0 1 0 12 8a3.5 3.5 0 0 0 0 7.5Z" />

                    <path
                        d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.12 2.12-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.04 1.55V20.3h-3v-.09a1.7 1.7 0 0 0-1.04-1.55 1.7 1.7 0 0 0-1.88.34l-.06.06-2.12-2.12.06-.06A1.7 1.7 0 0 0 7 15a1.7 1.7 0 0 0-1.55-1.04H5.3v-3h.15A1.7 1.7 0 0 0 7 9.92a1.7 1.7 0 0 0-.34-1.88l-.06-.06 2.12-2.12.06.06A1.7 1.7 0 0 0 10.66 6 1.7 1.7 0 0 0 11.7 4.45V4.3h3v.15A1.7 1.7 0 0 0 15.74 6a1.7 1.7 0 0 0 1.88-.34l.06-.06 2.12 2.12-.06.06A1.7 1.7 0 0 0 19.4 9.7a1.7 1.7 0 0 0 1.55 1.04h.15v3h-.15A1.7 1.7 0 0 0 19.4 15Z" />

                </svg>
            </span>

            <span class="nav__text">
                Configuración
            </span>

        </a>

    </nav>


    <!-- ======================================================
         FOOTER
         ====================================================== -->

    <div class="sidebar__footer">

        <div class="sidebar-user">

            <div class="sidebar-user__avatar">
                A
            </div>

            <div class="sidebar-user__info">
                <strong>Administrador</strong>
                <span>NOC Colombia</span>
            </div>

        </div>

        <div class="sidebar-version">
            RKP · v1.0
        </div>

    </div>

</aside>


<button class="sidebar-scrim" type="button" aria-label="Cerrar navegación" tabindex="-1"></button>