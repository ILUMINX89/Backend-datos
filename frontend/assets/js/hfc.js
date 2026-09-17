(() => {
    'use strict';

    const body = document.getElementById('hfc-rows');
    const status = document.getElementById('hfc-status');
    const panel = document.getElementById('alarmas');
    const refresh = document.getElementById('hfc-refresh');
    const summary = document.getElementById('hfc-summary');
    const table = document.getElementById('hfc-table');
    const number = new Intl.NumberFormat('es-CO', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
    let busy = false;

    function render(rows) {
        const fragment = document.createDocumentFragment();
        rows.forEach((row) => {
            const tr = document.createElement('tr');
            [row.equipo, row.puerto, `${number.format(Number(row.valor))} %`]
                .forEach((text) => {
                    const td = document.createElement('td');
                    td.textContent = text;
                    tr.append(td);
                });
            const state = document.createElement('td');
            const badge = document.createElement('span');
            badge.className = 'gkp-badge';
            badge.textContent = row.estado;
            badge.title = row.detalle || '';
            state.append(badge);
            tr.append(state);
            fragment.append(tr);
        });
        body.replaceChildren(fragment);
    }

    async function load({ silent = false } = {}) {
        if (busy) return;
        busy = true;
        refresh.disabled = true;
        panel.setAttribute('aria-busy', 'true');
        if (!silent) status.textContent = 'Consultando saturaciones CMTS…';

        try {
            const endpoint = new URL('../backend/api/hfc.php', window.location.href);
            const response = await fetch(endpoint, { cache: 'no-store' });
            const payload = await response.json();
            const rows = payload.data?.estado_actual_hfc;
            if (!response.ok || !payload.ok || !Array.isArray(rows)) {
                throw new Error('Respuesta no disponible');
            }
            render(rows);
            table.hidden = rows.length === 0;
            summary.textContent = rows.length === 1
                ? '1 puerto requiere revisión'
                : `${rows.length} puertos requieren revisión`;
            status.textContent = rows.length
                ? ''
                : 'Sin saturaciones CMTS por encima del 80%';
        } catch (_error) {
            status.textContent = 'No se pudo consultar el estado HFC. Se reintentará automáticamente.';
        } finally {
            busy = false;
            refresh.disabled = false;
            panel.setAttribute('aria-busy', 'false');
        }
    }

    if (!body || !status || !panel || !refresh || !summary || !table) return;
    refresh.addEventListener('click', () => load());
    load();
    setInterval(() => load({ silent: true }), 30000);
})();
