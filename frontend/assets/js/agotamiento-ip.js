(() => {
    'use strict';

    const panel = document.getElementById('intermitencias-ftth-panel');
    const rows = document.getElementById('intermitencias-ftth-rows');
    const status = document.getElementById('intermitencias-ftth-status');
    const table = document.getElementById('intermitencias-ftth-table');
    const summary = document.getElementById('intermitencias-ftth-summary');
    const refresh = document.getElementById('intermitencias-ftth-refresh');

    if (!panel || !rows || !status || !table || !summary || !refresh) {
        return;
    }

    let busy = false;

    const crearCelda = (valor) => {
        const td = document.createElement('td');
        td.textContent = valor === null || valor === undefined || valor === '' ? '—' : String(valor);
        return td;
    };

    const mostrarEstado = (mensaje, resumen) => {
        rows.replaceChildren();
        table.hidden = true;
        status.style.display = '';
        status.textContent = mensaje;
        summary.textContent = resumen;
    };

    const render = (items) => {
        if (!items.length) {
            mostrarEstado('No se detectaron intermitencias FTTH en los últimos 2 días.', '0 intermitencias detectadas');
            return;
        }

        const ordenados = [...items].sort((a, b) =>
            (Number(b.cantidad_caidas) || 0) - (Number(a.cantidad_caidas) || 0)
            || String(b.dia ?? '').localeCompare(String(a.dia ?? ''))
        );
        const fragment = document.createDocumentFragment();

        ordenados.forEach((item) => {
            const tr = document.createElement('tr');
            const cantidad = item.cantidad_caidas;
            const minutos = item.tiempo_total_caido_minutos;
            const numeroCaidas = Number(cantidad);
            const numeroMinutos = Number(minutos);
            tr.append(
                crearCelda(item.olt),
                crearCelda(item.puerto),
                crearCelda(item.dia),
                crearCelda(cantidad === null || cantidad === undefined || cantidad === '' || !Number.isFinite(numeroCaidas)
                    ? null
                    : Math.trunc(numeroCaidas)),
                crearCelda(minutos === null || minutos === undefined || minutos === '' || !Number.isFinite(numeroMinutos)
                    ? null
                    : `${Number(numeroMinutos.toFixed(2))} min`),
            );
            fragment.appendChild(tr);
        });

        rows.replaceChildren(fragment);
        table.hidden = false;
        status.style.display = 'none';
        status.textContent = '';
        summary.textContent = items.length === 1 ? '1 intermitencia detectada' : `${items.length} intermitencias detectadas`;
    };

    const load = async () => {
        if (busy) return;

        busy = true;
        refresh.disabled = true;
        panel.setAttribute('aria-busy', 'true');
        mostrarEstado('Cargando…', 'Consultando información disponible…');

        try {
            const response = await fetch('../backend/api/intermitencias_ftth.php', { cache: 'no-store' });
            const payload = await response.json();
            const items = payload.data?.intermitencias;

            if (!response.ok || payload.ok !== true || !Array.isArray(items)) {
                throw new Error('Respuesta inválida del servicio');
            }
            render(items);
        } catch (error) {
            console.error('Error consultando intermitencias FTTH:', error);
            mostrarEstado('No se pudo consultar la información. Intente actualizar nuevamente.', 'Error de consulta');
        } finally {
            busy = false;
            refresh.disabled = false;
            panel.setAttribute('aria-busy', 'false');
        }
    };

    refresh.addEventListener('click', load);
    load();
})();
