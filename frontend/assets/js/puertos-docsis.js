(() => {
    'use strict';

    const rows = document.getElementById('puertos-docsis-rows');
    const status = document.getElementById('puertos-docsis-status');
    const table = document.getElementById('puertos-docsis-table');
    const panel = document.getElementById('puertos-docsis-panel');
    const summary = document.getElementById('puertos-docsis-summary');
    const refresh = document.getElementById('puertos-docsis-refresh');
    if (!rows || !status || !table || !panel || !summary || !refresh) return;

    let busy = false;

    const render = (items) => {
        const resultRows = items.map((item) => {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.textContent = typeof item === 'string' ? item : JSON.stringify(item);
            tr.append(td);
            return tr;
        });
        rows.replaceChildren(...resultRows);
        table.hidden = items.length === 0;
        status.style.display = items.length > 0 ? 'none' : '';
        status.textContent = items.length ? '' : 'Sin datos disponibles';
        summary.textContent = items.length === 1 ? '1 resultado disponible' : `${items.length} resultados disponibles`;
    };

    const load = async () => {
        if (busy) return;
        busy = true;
        refresh.disabled = true;
        panel.setAttribute('aria-busy', 'true');
        table.hidden = true;
        status.style.display = '';
        status.textContent = 'Cargando…';
        summary.textContent = 'Consultando información disponible…';
        try {
            const response = await fetch('../backend/api/puertos_docsis.php', { cache: 'no-store' });
            const payload = await response.json();
            if (!response.ok || payload.ok !== true || !Array.isArray(payload.data?.puertos_docsis)) {
                throw new Error('Respuesta inválida');
            }
            render(payload.data.puertos_docsis);
        } catch (_error) {
            rows.replaceChildren();
            status.style.display = '';
            status.textContent = 'No se pudo consultar la información de puertos DOCSIS.';
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
