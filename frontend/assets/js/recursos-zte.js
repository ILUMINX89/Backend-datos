(() => {
    'use strict';

    const rows = document.getElementById('recursos-zte-rows');
    const status = document.getElementById('recursos-zte-status');
    const table = document.getElementById('recursos-zte-table');
    const panel = document.getElementById('recursos-zte-panel');
    const summary = document.getElementById('recursos-zte-summary');
    const refresh = document.getElementById('recursos-zte-refresh');
    if (!rows || !status || !table || !panel || !summary || !refresh) return;

    let busy = false;
    const numberFormat = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 2 });
    const formatPercent = (value) => `${numberFormat.format(value)}%`;

    const render = (licencias) => {
        const fragment = document.createDocumentFragment();
        licencias.forEach((licencia) => {
            const tr = document.createElement('tr');
            [
                licencia.olt,
                licencia.recurso,
                numberFormat.format(licencia.usado),
                numberFormat.format(licencia.disponible),
                numberFormat.format(licencia.total),
                formatPercent(licencia.porcentaje_disponible),
                licencia.actualizado_en,
            ].forEach((value) => {
                const td = document.createElement('td');
                td.textContent = value;
                tr.append(td);
            });
            fragment.append(tr);
        });
        rows.replaceChildren(fragment);
        table.hidden = licencias.length === 0;
        status.style.display = licencias.length > 0 ? 'none' : '';
        status.textContent = licencias.length ? '' : 'No hay licencias ZTE con menos del 15% disponible.';
        summary.textContent = licencias.length === 1
            ? '1 licencia con baja disponibilidad'
            : `${licencias.length} licencias con baja disponibilidad`;
    };

    const load = async () => {
        if (busy) return;
        busy = true;
        refresh.disabled = true;
        panel.setAttribute('aria-busy', 'true');
        table.hidden = true;
        status.style.display = '';
        status.textContent = 'Cargando…';
        summary.textContent = 'Consultando disponibilidad…';
        try {
            const response = await fetch('../backend/api/recursos_zte.php', { cache: 'no-store' });
            const payload = await response.json();
            if (!response.ok || payload.ok !== true || !Array.isArray(payload.data?.licencias)) {
                throw new Error('Respuesta inválida');
            }
            render(payload.data.licencias);
        } catch (_error) {
            rows.replaceChildren();
            table.hidden = true;
            status.style.display = '';
            status.textContent = 'No se pudo consultar la disponibilidad de licencias ZTE.';
            summary.textContent = 'Error de consulta';
        } finally {
            busy = false;
            refresh.disabled = false;
            panel.setAttribute('aria-busy', 'false');
        }
    };

    refresh.addEventListener('click', load);
    load();
})();
