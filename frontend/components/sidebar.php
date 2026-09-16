<aside id="main-sidebar" class="sidebar" aria-label="Navegación principal">
    <div class="sidebar__top">
        <a href="index.php" class="sidebar-brand">
            <div class="sidebar-brand__icon" aria-hidden="true">
                <span class="brand-signal brand-signal--1"></span>
                <span class="brand-signal brand-signal--2"></span>
                <span class="brand-signal brand-signal--3"></span>
                <span class="brand-signal__core"></span>
            </div>
            <div class="sidebar-brand__text">
                <strong>NOC BOA</strong>
                <span>Operación FTTH / HFC</span>
            </div>
        </a>
        <div class="sidebar-system">
            <span class="sidebar-system__dot" aria-hidden="true"></span>
            <div>
                <strong id="sidebar-monitoring">Consultando</strong>
                <small id="sidebar-monitoring-detail">Esperando datos</small>
            </div>
        </div>
    </div>

    <nav class="nav" aria-label="Módulos">
        <span class="nav__section">Operación</span>
        <a class="nav__item active" href="index.php" aria-current="page">
            <span class="nav__icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 10.5 12 3l9 7.5v9a1.5 1.5 0 0 1-1.5 1.5H15v-6H9v6H4.5A1.5 1.5 0 0 1 3 19.5z"/></svg></span>
            <span class="nav__text">Vista general</span>
        </a>
        <a class="nav__item" href="index.php#alarmas">
            <span class="nav__icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></svg></span>
            <span class="nav__text">Alarmas</span>
            <span id="sidebar-total" class="sidebar-badge">0</span>
        </a>
        <span class="nav__section nav__section--secondary">Gestión</span>
        <a class="nav__item" href="reportes.php">
            <span class="nav__icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 19V9m6 10V5m6 14v-7m4 7H2"/></svg></span>
            <span class="nav__text">Reportes</span>
        </a>
        <a class="nav__item" href="configuracion.php">
            <span class="nav__icon"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 15.5A3.5 3.5 0 1 0 12 8a3.5 3.5 0 0 0 0 7.5Z"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.12 2.12-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.04 1.55V20.3h-3v-.09a1.7 1.7 0 0 0-1.04-1.55 1.7 1.7 0 0 0-1.88.34l-.06.06-2.12-2.12.06-.06A1.7 1.7 0 0 0 7 15a1.7 1.7 0 0 0-1.55-1.04H5.3v-3h.15A1.7 1.7 0 0 0 7 9.92a1.7 1.7 0 0 0-.34-1.88l-.06-.06 2.12-2.12.06.06A1.7 1.7 0 0 0 10.66 6 1.7 1.7 0 0 0 11.7 4.45V4.3h3v.15A1.7 1.7 0 0 0 15.74 6a1.7 1.7 0 0 0 1.88-.34l.06-.06 2.12 2.12-.06.06A1.7 1.7 0 0 0 19.4 9.7a1.7 1.7 0 0 0 1.55 1.04h.15v3h-.15A1.7 1.7 0 0 0 19.4 15Z"/></svg></span>
            <span class="nav__text">Configuración</span>
        </a>
    </nav>

    <div class="sidebar__footer">
        <div class="sidebar-user">
            <div class="sidebar-user__avatar">A</div>
            <div class="sidebar-user__info">
                <strong>Administrador</strong>
                <span>NOC Colombia</span>
            </div>
        </div>
        <div class="sidebar-version">NOC BOA · v1.0</div>
    </div>
</aside>
