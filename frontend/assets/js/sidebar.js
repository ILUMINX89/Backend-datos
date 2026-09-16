(() => {
    const STORAGE_KEY = 'noc-boa-sidebar-collapsed';
    const page = document.body;
    const toggle = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('main-sidebar');
    const desktop = window.matchMedia('(min-width: 861px)');

    if (!toggle || !sidebar) return;

    let preferredCollapsed = false;

    const applyState = () => {
        const collapsed = desktop.matches && preferredCollapsed;

        page.classList.toggle('sidebar-collapsed', collapsed);
        sidebar.toggleAttribute('inert', collapsed);
        sidebar.setAttribute('aria-hidden', String(collapsed));
        toggle.setAttribute('aria-expanded', String(!collapsed));

        const action = collapsed ? 'Mostrar barra lateral' : 'Ocultar barra lateral';
        toggle.setAttribute('aria-label', action);
        toggle.title = action;
    };

    try {
        preferredCollapsed = localStorage.getItem(STORAGE_KEY) === 'true';
    } catch (_) {
        // La interfaz sigue funcionando aunque el navegador bloquee el almacenamiento.
    }

    applyState();

    toggle.addEventListener('click', () => {
        preferredCollapsed = !page.classList.contains('sidebar-collapsed');
        applyState();

        try {
            localStorage.setItem(STORAGE_KEY, String(preferredCollapsed));
        } catch (_) {
            // Mantener el estado de esta sesión sin interrumpir el control.
        }
    });

    desktop.addEventListener('change', applyState);
})();
