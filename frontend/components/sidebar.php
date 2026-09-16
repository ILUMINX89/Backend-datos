<?php
$sidebarPage = basename($_SERVER['PHP_SELF'] ?? 'index.php');
$sidebarModule = isset($_GET['module']) ? (string) $_GET['module'] : '';
$sidebarView = isset($_GET['view']) ? (string) $_GET['view'] : '';
$uplinkViews = ['saturaciones', 'caidas', 'atenuaciones', 'intermitencias'];
$ponViews = ['duplicadas', 'atenuadas'];
$overviewActive = $sidebarPage === 'index.php' && $sidebarModule === '';
$uplinkActive = $sidebarModule === 'uplink' && in_array($sidebarView, $uplinkViews, true);
$ponActive = $sidebarModule === 'pon' && in_array($sidebarView, $ponViews, true);
?>
<aside id="main-sidebar" class="sidebar" aria-label="Navegación principal">
    <div class="sidebar__top">
        <a href="index.php" class="sidebar-brand">
            <div class="sidebar-brand__icon" aria-hidden="true">
                <span class="brand-signal brand-signal--1"></span><span class="brand-signal brand-signal--2"></span>
                <span class="brand-signal brand-signal--3"></span><span class="brand-signal__core"></span>
            </div>
            <div class="sidebar-brand__text"><strong>RKP</strong><span>Operación FTTH / HFC</span></div>
        </a>
        <div class="sidebar-system">
            <span class="sidebar-system__dot" aria-hidden="true"></span>
            <div><strong id="sidebar-monitoring">Consultando</strong><small id="sidebar-monitoring-detail">Esperando datos</small></div>
        </div>
    </div>

    <nav class="nav" aria-label="Módulos">
        <span class="nav__section">Operación</span>
        <a class="nav__item<?= $overviewActive ? ' active' : '' ?>" href="index.php"<?= $overviewActive ? ' aria-current="page"' : '' ?>>
            <span class="nav__icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 10.5 12 3l9 7.5v9a1.5 1.5 0 0 1-1.5 1.5H15v-6H9v6H4.5A1.5 1.5 0 0 1 3 19.5z"/></svg></span>
            <span class="nav__text">Vista general</span>
        </a>

        <span class="nav__section nav__section--ftth">FTTH</span>
        <div class="nav__group<?= $uplinkActive ? ' is-active' : '' ?>" data-nav-group="uplink">
            <button class="nav__item nav__toggle" type="button" aria-expanded="<?= $uplinkActive ? 'true' : 'false' ?>" aria-controls="submenu-uplink-ftth">
                <span class="nav__icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 18h14M7 14h10M9 10h6M12 6v12"/></svg></span>
                <span class="nav__text">Puertos Uplink</span>
                <svg class="nav__chevron" viewBox="0 0 16 16" aria-hidden="true"><path d="m4 6 4 4 4-4"/></svg>
            </button>
            <div id="submenu-uplink-ftth" class="nav__submenu"<?= $uplinkActive ? '' : ' hidden' ?>>
                <?php foreach (['saturaciones' => 'Saturaciones', 'caidas' => 'Caídas', 'atenuaciones' => 'Atenuaciones', 'intermitencias' => 'Intermitencias'] as $view => $label): ?>
                    <button class="nav__subitem<?= $sidebarModule === 'uplink' && $sidebarView === $view ? ' active' : '' ?>" type="button" aria-disabled="true" title="Módulo pendiente de implementación"><?= htmlspecialchars($label, ENT_QUOTES, 'UTF-8') ?></button>
                <?php endforeach; ?>
            </div>
        </div>

        <?php foreach ([
            ['Recursos ZTE', 'M4 5h16v14H4zM8 9h8M8 13h8M8 17h5'],
            ['Autofind HW', 'M12 3a9 9 0 1 0 9 9M12 7a5 5 0 1 0 5 5M12 11a1 1 0 1 0 1 1'],
            ['ONTs Unconfig', 'M5 18V8l7-5 7 5v10M8 18v-5h8v5M3 21h18'],
        ] as [$label, $icon]): ?>
            <button class="nav__item nav__item--pending" type="button" aria-disabled="true" title="Módulo pendiente de implementación">
                <span class="nav__icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="<?= $icon ?>"/></svg></span>
                <span class="nav__text"><?= htmlspecialchars($label, ENT_QUOTES, 'UTF-8') ?></span>
                <span class="nav__pending" aria-hidden="true">Próx.</span>
            </button>
        <?php endforeach; ?>

        <div class="nav__group<?= $ponActive ? ' is-active' : '' ?>" data-nav-group="pon">
            <button class="nav__item nav__toggle" type="button" aria-expanded="<?= $ponActive ? 'true' : 'false' ?>" aria-controls="submenu-pon-ftth">
                <span class="nav__icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M6 12h12M8 17h8M12 7v10"/></svg></span>
                <span class="nav__text">Troncales PON</span>
                <svg class="nav__chevron" viewBox="0 0 16 16" aria-hidden="true"><path d="m4 6 4 4 4-4"/></svg>
            </button>
            <div id="submenu-pon-ftth" class="nav__submenu"<?= $ponActive ? '' : ' hidden' ?>>
                <?php foreach (['duplicadas' => 'Troncales duplicadas', 'atenuadas' => 'Troncales atenuadas'] as $view => $label): ?>
                    <button class="nav__subitem<?= $sidebarModule === 'pon' && $sidebarView === $view ? ' active' : '' ?>" type="button" aria-disabled="true" title="Módulo pendiente de implementación"><?= htmlspecialchars($label, ENT_QUOTES, 'UTF-8') ?></button>
                <?php endforeach; ?>
            </div>
        </div>

        <button class="nav__item nav__item--pending" type="button" aria-disabled="true" title="Módulo pendiente de implementación">
            <span class="nav__icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 12h5l2-6 3 12 2-6h4"/></svg></span>
            <span class="nav__text">Agotamiento de IP</span><span class="nav__pending" aria-hidden="true">Próx.</span>
        </button>

        <span class="nav__section nav__section--secondary">Gestión</span>
        <a class="nav__item<?= $sidebarPage === 'reportes.php' ? ' active' : '' ?>" href="reportes.php"<?= $sidebarPage === 'reportes.php' ? ' aria-current="page"' : '' ?>>
            <span class="nav__icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 19V9m6 10V5m6 14v-7m4 7H2"/></svg></span><span class="nav__text">Reportes</span>
        </a>
        <a class="nav__item<?= $sidebarPage === 'configuracion.php' ? ' active' : '' ?>" href="configuracion.php"<?= $sidebarPage === 'configuracion.php' ? ' aria-current="page"' : '' ?>>
            <span class="nav__icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 15.5A3.5 3.5 0 1 0 12 8a3.5 3.5 0 0 0 0 7.5Z"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.12 2.12-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.04 1.55V20.3h-3v-.09a1.7 1.7 0 0 0-1.04-1.55 1.7 1.7 0 0 0-1.88.34l-.06.06-2.12-2.12.06-.06A1.7 1.7 0 0 0 7 15a1.7 1.7 0 0 0-1.55-1.04H5.3v-3h.15A1.7 1.7 0 0 0 7 9.92a1.7 1.7 0 0 0-.34-1.88l-.06-.06 2.12-2.12.06.06A1.7 1.7 0 0 0 10.66 6 1.7 1.7 0 0 0 11.7 4.45V4.3h3v.15A1.7 1.7 0 0 0 15.74 6a1.7 1.7 0 0 0 1.88-.34l.06-.06 2.12 2.12-.06.06A1.7 1.7 0 0 0 19.4 9.7a1.7 1.7 0 0 0 1.55 1.04h.15v3h-.15A1.7 1.7 0 0 0 19.4 15Z"/></svg></span><span class="nav__text">Configuración</span>
        </a>
    </nav>

    <div class="sidebar__footer">
        <div class="sidebar-user"><div class="sidebar-user__avatar">A</div><div class="sidebar-user__info"><strong>Administrador</strong><span>NOC Colombia</span></div></div>
        <div class="sidebar-version">RKP · v1.0</div>
    </div>
</aside>
<button class="sidebar-scrim" type="button" aria-label="Cerrar navegación" tabindex="-1"></button>
