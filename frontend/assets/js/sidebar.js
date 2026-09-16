(() => {
    const COLLAPSED_KEY = 'noc-boa-sidebar-collapsed';
    const GROUPS_KEY = 'noc-boa-sidebar-groups';
    const page = document.body;
    const toggle = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('main-sidebar');
    const scrim = document.querySelector('.sidebar-scrim');
    const wideScreen = window.matchMedia('(min-width: 1024px)');

    if (!toggle || !sidebar) return;

    let preferredCollapsed = false;
    let openGroups = new Set();

    try {
        preferredCollapsed = localStorage.getItem(COLLAPSED_KEY) === 'true';
        openGroups = new Set(JSON.parse(localStorage.getItem(GROUPS_KEY) || '[]'));
    } catch (_) {
        // La navegación conserva su estado durante la sesión si el almacenamiento está bloqueado.
    }

    const setGroup = (group, open) => {
        const button = group.querySelector('.nav__toggle');
        const submenu = document.getElementById(button.getAttribute('aria-controls'));
        button.setAttribute('aria-expanded', String(open));
        submenu.hidden = !open;
        group.classList.toggle('is-open', open);
    };

    document.querySelectorAll('[data-nav-group]').forEach((group) => {
        const name = group.dataset.navGroup;
        setGroup(group, group.classList.contains('is-active') || openGroups.has(name));

        group.querySelector('.nav__toggle').addEventListener('click', () => {
            const open = group.querySelector('.nav__toggle').getAttribute('aria-expanded') !== 'true';
            setGroup(group, open);
            open ? openGroups.add(name) : openGroups.delete(name);
            try { localStorage.setItem(GROUPS_KEY, JSON.stringify([...openGroups])); } catch (_) {}
        });
    });

    const applyLayout = () => {
        if (wideScreen.matches) {
            page.classList.remove('sidebar-open');
            page.classList.toggle('sidebar-collapsed', preferredCollapsed);
            sidebar.toggleAttribute('inert', preferredCollapsed);
            sidebar.setAttribute('aria-hidden', String(preferredCollapsed));
            toggle.setAttribute('aria-expanded', String(!preferredCollapsed));
            toggle.setAttribute('aria-label', preferredCollapsed ? 'Mostrar barra lateral' : 'Ocultar barra lateral');
        } else {
            page.classList.remove('sidebar-collapsed');
            const open = page.classList.contains('sidebar-open');
            sidebar.toggleAttribute('inert', !open);
            sidebar.setAttribute('aria-hidden', String(!open));
            toggle.setAttribute('aria-expanded', String(open));
            toggle.setAttribute('aria-label', open ? 'Cerrar navegación' : 'Abrir navegación');
        }
        toggle.title = toggle.getAttribute('aria-label');
    };

    const closeDrawer = () => {
        page.classList.remove('sidebar-open');
        applyLayout();
    };

    toggle.addEventListener('click', () => {
        if (wideScreen.matches) {
            preferredCollapsed = !page.classList.contains('sidebar-collapsed');
            try { localStorage.setItem(COLLAPSED_KEY, String(preferredCollapsed)); } catch (_) {}
        } else {
            page.classList.toggle('sidebar-open');
        }
        applyLayout();
    });

    scrim?.addEventListener('click', closeDrawer);
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && page.classList.contains('sidebar-open')) {
            closeDrawer();
            toggle.focus();
        }
    });
    wideScreen.addEventListener('change', applyLayout);
    applyLayout();
})();
