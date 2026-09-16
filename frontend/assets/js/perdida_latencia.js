(() => {
    'use strict';

    const panel = document.getElementById('perdida-latencia-panel');
    const rows = document.getElementById('perdida-latencia-rows');
    const status = document.getElementById('perdida-latencia-status');
    const updated = document.getElementById('perdida-latencia-updated');
    const tableRegion = document.getElementById('perdida-latencia-table-region');
    const empty = document.getElementById('perdida-latencia-empty');
    const count = document.getElementById('perdida-latencia-count');
    let busy = false;

    function formatNumber(value, suffix = '') {
        const number = Number(value);
        return Number.isFinite(number) ? `${number.toFixed(2)}${suffix}` : '—';
    }

    function render(data) {
        const fragment = document.createDocumentFragment();

        for (const item of data) {
            const row = document.createElement('tr');
            const equipo = document.createElement('td');
            const perdida = document.createElement('td');
            const latencia = document.createElement('td');
            const estado = document.createElement('td');
            const tiempo = document.createElement('td');

            equipo.textContent = item.equipo || 'N/D';
            equipo.className = 'gkp-equipment';
            perdida.textContent = formatNumber(item.perdida, '%');
            latencia.textContent = formatNumber(
                item.latencia,
                item.unidad_latencia ? ` ${item.unidad_latencia}` : ''
            );
            estado.textContent = item.estado || '—';
            tiempo.textContent = item.tiempo || '—';
            row.append(equipo, perdida, latencia, estado, tiempo);
            fragment.appendChild(row);
        }

        rows.replaceChildren(fragment);
        tableRegion.hidden = data.length === 0;
        empty.hidden = data.length !== 0;
        count.textContent = String(data.length);
    }

    async function load() {
        if (busy) return;
        busy = true;
        panel.setAttribute('aria-busy', 'true');
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 20000);

        try {
            const response = await fetch('../backend/api/perdida_latencia.php', {
                cache: 'no-store',
                signal: controller.signal,
            });
            if (!response.ok) throw new Error('HTTP inválido');
            const payload = await response.json();
            if (payload.ok !== true || !Array.isArray(payload.data?.datos)) {
                throw new Error('Respuesta inválida');
            }
            render(payload.data.datos);
            status.textContent = '';
            updated.textContent = `Última actualización: ${new Date().toLocaleString('es-CO')}`;
        } catch (error) {
            rows.replaceChildren();
            tableRegion.hidden = false;
            empty.hidden = true;
            count.textContent = '—';
            status.textContent = 'No se pudo consultar pérdida y latencia. Se reintentará automáticamente.';
        } finally {
            clearTimeout(timeout);
            busy = false;
            panel.setAttribute('aria-busy', 'false');
        }
    }

    document.getElementById('gkp-refresh')?.addEventListener('click', load);
    load();
    setInterval(load, 30000);
})();
