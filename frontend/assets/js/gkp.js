(() => {
    'use strict';

    const body = document.getElementById('gkp-rows');
    const status = document.getElementById('gkp-status');
    const panel = document.getElementById('alarmas');
    const refresh = document.getElementById('gkp-refresh');

    const number = new Intl.NumberFormat('es-CO', {
        maximumFractionDigits: 2
    });

    let busy = false;
    let hasValidData = false;

    function setText(id, text) {
        const element = document.getElementById(id);

        if (element) {
            element.textContent = text;
        }
    }

    function formatValue(row) {
        if (row.valor === null || row.valor === undefined) {
            return 'N/D';
        }

        const valor = Number(row.valor);

        if (!Number.isFinite(valor)) {
            return 'N/D';
        }

        /*
         * DURACIÓN DE CAÍDAS
         *
         * El backend entrega minutos.
         *
         * Se muestran como:
         *
         * 10 min  -> 0.10 h
         * 25 min  -> 0.25 h
         * 60 min  -> 1.00 h
         * 75 min  -> 1.15 h
         * 90 min  -> 1.30 h
         *
         * Es formato HH.MM, no horas decimales matemáticas.
         */
        if (row.unidad === 'min') {
            const totalMinutos = Math.max(
                0,
                Math.round(valor)
            );

            const horas = Math.floor(
                totalMinutos / 60
            );

            const minutos = totalMinutos % 60;

            return (
                `${horas}.` +
                `${String(minutos).padStart(2, '0')} h`
            );
        }

        /*
         * OTRAS UNIDADES
         *
         * Saturación:
         * 92.45 %
         *
         * CRC:
         * 14,81 CRC/s
         */
        return `${number.format(valor)} ${row.unidad}`;
    }

    function render(rows) {
        const fragment = document.createDocumentFragment();
        const seen = new Set();

        rows.forEach((row, index) => {
            const tr = document.createElement('tr');

            /*
             * Agrupar equipos consecutivos.
             */
            if (
                index === 0 ||
                rows[index - 1].equipo !== row.equipo
            ) {
                const td = document.createElement('td');

                td.className = 'gkp-equipment';

                let end = index + 1;

                while (
                    end < rows.length &&
                    rows[end].equipo === row.equipo
                ) {
                    end++;
                }

                td.rowSpan = end - index;

                td.textContent = seen.has(row.equipo)
                    ? ''
                    : row.equipo;

                td.setAttribute(
                    'aria-label',
                    row.equipo
                );

                seen.add(row.equipo);

                tr.append(td);
            }

            /*
             * Puerto.
             */
            const port = document.createElement('td');

            port.textContent = row.puerto;

            port.setAttribute(
                'aria-label',
                `${row.equipo}: ${row.puerto}`
            );

            /*
             * Valor.
             */
            const value = document.createElement('td');

            value.textContent = formatValue(row);

            value.title = row.detalle || '';

            const down = row.estado === 'Caída actual';

            if (down) {
                value.className = 'gkp-value--down';
            }

            /*
             * Estado.
             */
            const state = document.createElement('td');

            const badge = document.createElement('span');

            badge.className =
                `gkp-badge${down ? ' gkp-badge--down' : ''}`;

            badge.textContent = row.estado;

            badge.title = row.detalle || '';

            state.append(badge);

            tr.append(
                port,
                value,
                state
            );

            fragment.append(tr);
        });

        body.replaceChildren(fragment);
    }

    function connection(text, detail) {
        setText('header-connection', text);

        const dot = document.querySelector(
            '.connection-dot'
        );

        const card = document.querySelector(
            '.topbar-card--connection'
        );

        if (dot) {
            dot.classList.toggle(
                'offline',
                text !== 'Conectado'
            );

            dot.classList.toggle(
                'online',
                text === 'Conectado'
            );
        }

        if (card) {
            card.classList.toggle(
                'is-online',
                text === 'Conectado'
            );
        }

        setText('header-connection-detail', detail);
    }

    function monitoring(text, detail, tone) {
        setText('header-monitoring', text);
        setText('header-monitoring-detail', detail);
        setText('sidebar-monitoring', text);
        setText('sidebar-monitoring-detail', detail);

        document.querySelectorAll(
            '.monitor-dot, .sidebar-system__dot'
        ).forEach((dot) => {
            dot.classList.toggle('available', tone === 'available');
            dot.classList.toggle('partial', tone === 'partial');
            dot.classList.toggle('error', tone === 'error');
        });

        document.querySelectorAll(
            '.topbar-card--monitoring, .sidebar-system'
        ).forEach((surface) => {
            surface.classList.toggle('is-available', tone === 'available');
            surface.classList.toggle('is-partial', tone === 'partial');
            surface.classList.toggle('is-error', tone === 'error');
        });
    }

    async function load({ silent = false } = {}) {
        if (busy) {
            return;
        }

        busy = true;

        refresh.disabled = true;

        if (!silent) {
            status.textContent = 'Consultando el estado de la red…';
        }

        panel.setAttribute(
            'aria-busy',
            'true'
        );

        const controller = new AbortController();

        const timeout = setTimeout(
            () => controller.abort(),
            185000
        );

        try {
            const endpoint = new URL(
                '../backend/api/gkp.php',
                window.location.href
            );

            const response = await fetch(
                endpoint,
                {
                    cache: 'no-store',
                    signal: controller.signal
                }
            );

            const payload = await response.json();

            if (
                !response.ok ||
                !payload.ok ||
                !Array.isArray(
                    payload.data?.estado_actual_red
                )
            ) {
                throw new Error(
                    'Respuesta no disponible'
                );
            }

            const rows =
                payload.data.estado_actual_red;

            render(rows);
            hasValidData = true;

            const sourceEntries = Object.entries(
                payload.sources || {}
            );

            const failed = sourceEntries
                .filter(
                    ([, source]) => !source.ok
                )
                .map(
                    ([name]) => name
                );

            setText('gkp-count', String(rows.length));

            setText('gkp-summary', rows.length === 1
                ? '1 excepción requiere revisión'
                : `${rows.length} excepciones requieren revisión`);

            const sources = document.getElementById(
                'header-sources'
            );

            if (sources) {
                sources.textContent = sourceEntries.length
                    ? `${sourceEntries.length - failed.length} / ${sourceEntries.length} disponibles`
                    : 'Sin información';
            }

            monitoring(
                failed.length ? 'Parcial' : 'Disponible',
                sourceEntries.length
                    ? `${sourceEntries.length - failed.length} de ${sourceEntries.length} fuentes`
                    : 'Consulta completada',
                failed.length ? 'partial' : 'available'
            );

            status.textContent = failed.length
                ? (
                    'Información parcial. ' +
                    'Fuentes no disponibles: ' +
                    `${failed.join(', ')}. ` +
                    'Se reintentará automáticamente.'
                )
                : (
                    rows.length
                        ? ''
                        : (
                            'Sin eventos reportados ' +
                            'por las fuentes consultadas.'
                        )
                );

            const now = new Date()
                .toLocaleString('es-CO');

            setText('gkp-updated', `Última actualización: ${now}`);
            setText('header-datetime', now);

            connection(
                failed.length
                    ? 'Conexión parcial'
                    : 'Conectado',
                'Actualización cada 30 segundos'
            );
        } catch (error) {
            if (!hasValidData) {
                body.replaceChildren();
                setText('gkp-count', '—');
                setText('gkp-summary', 'Estado operacional no disponible');
            }

            status.textContent = error?.name === 'AbortError'
                ? 'La consulta excedió el tiempo disponible. Se reintentará automáticamente; también puedes pulsar Actualizar.'
                : 'No se pudo consultar el estado de la red. Se reintentará automáticamente; también puedes pulsar Actualizar.';

            connection(
                'Sin conexión',
                'Consulta fallida'
            );

            const sources = document.getElementById(
                'header-sources'
            );

            if (sources && !hasValidData) {
                sources.textContent = 'No disponibles';
            }

            monitoring(
                'Error',
                'Consulta no disponible',
                'error'
            );
        } finally {
            clearTimeout(timeout);

            busy = false;

            refresh.disabled = false;

            panel.setAttribute(
                'aria-busy',
                'false'
            );
        }
    }

    if (!body || !status || !panel || !refresh) {
        return;
    }

    setText('header-datetime', 'Pendiente');

    refresh.addEventListener(
        'click',
        () => load({ silent: false })
    );

    load();

    setInterval(
        () => load({ silent: true }),
        30000
    );
})();
