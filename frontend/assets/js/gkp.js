(() => {
    'use strict';
    const body = document.getElementById('gkp-rows');
    const status = document.getElementById('gkp-status');
    const panel = document.getElementById('alarmas');
    const refresh = document.getElementById('gkp-refresh');
    const number = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 2 });
    let busy = false;

    function render(rows) {
        const fragment = document.createDocumentFragment();
        const seen = new Set();
        rows.forEach((row, index) => {
            const tr = document.createElement('tr');
            // Merge contiguous equipment; suppress repeated names across state blocks.
            if (index === 0 || rows[index - 1].equipo !== row.equipo) {
                const td = document.createElement('td');
                td.className = 'gkp-equipment';
                let end = index + 1;
                while (end < rows.length && rows[end].equipo === row.equipo) end++;
                td.rowSpan = end - index;
                td.textContent = seen.has(row.equipo) ? '' : row.equipo;
                td.setAttribute('aria-label', row.equipo);
                seen.add(row.equipo);
                tr.append(td);
            }
            const port = document.createElement('td');
            port.textContent = row.puerto;
            port.setAttribute('aria-label', `${row.equipo}: ${row.puerto}`);
            const value = document.createElement('td');
            value.textContent = row.valor === null ? 'N/D' : `${number.format(row.valor)} ${row.unidad}`;
            value.title = row.detalle;
            const down = row.estado === 'Caída actual';
            if (down) value.className = 'gkp-value--down';
            const state = document.createElement('td');
            const badge = document.createElement('span');
            badge.className = `gkp-badge${down ? ' gkp-badge--down' : ''}`;
            badge.textContent = row.estado;
            badge.title = row.detalle;
            state.append(badge);
            tr.append(port, value, state);
            fragment.append(tr);
        });
        body.replaceChildren(fragment);
    }

    function connection(text, detail) {
        document.getElementById('header-connection').textContent = text;
        const dot = document.querySelector('.connection-dot');
        if (dot) dot.classList.toggle('offline', text !== 'Conectado');
        document.getElementById('header-connection-detail').textContent = detail;
    }

    async function load() {
        if (busy) return;
        busy = true;
        refresh.disabled = true;
        panel.setAttribute('aria-busy', 'true');
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 185000);
        try {
            const response = await fetch('/backend/api/gkp.php', { cache: 'no-store', signal: controller.signal });
            const payload = await response.json();
            if (!response.ok || !payload.ok || !Array.isArray(payload.data?.estado_actual_red)) {
                throw new Error('Respuesta no disponible');
            }
            const rows = payload.data.estado_actual_red;
            render(rows);
            const failed = Object.entries(payload.sources || {}).filter(([, source]) => !source.ok).map(([name]) => name);
            status.textContent = failed.length
                ? `Información parcial. Fuentes no disponibles: ${failed.join(', ')}. Se reintentará automáticamente.`
                : rows.length ? '' : 'Sin eventos reportados por las fuentes consultadas.';
            const now = new Date().toLocaleString('es-CO');
            document.getElementById('gkp-updated').textContent = `Última actualización: ${now}`;
            document.getElementById('header-datetime').textContent = now;
            document.getElementById('sidebar-total').textContent = String(rows.length);
            connection(failed.length ? 'Conexión parcial' : 'Conectado', 'Actualización cada 30 segundos');
        } catch {
            body.replaceChildren();
            document.getElementById('sidebar-total').textContent = '—';
            status.textContent = 'No se pudo consultar el estado de la red. Reintentando automáticamente; también puedes pulsar Actualizar.';
            connection('Sin conexión', 'Consulta fallida');
        } finally {
            clearTimeout(timeout);
            busy = false;
            refresh.disabled = false;
            panel.setAttribute('aria-busy', 'false');
        }
    }
    document.getElementById('header-datetime').textContent = 'Pendiente';
    document.getElementById('sidebar-total').textContent = '—';
    refresh.addEventListener('click', load);
    load();
    setInterval(load, 30000);
})();
