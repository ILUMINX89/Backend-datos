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
    let ftthSelectedRow = null;
    let ftthSelectedDays = 1;
    let ftthPowerVisible = false;
    let ftthCrcVisible = false;
    let ftthReturnFocus = null;

    const app = document.querySelector('.app');
    const ftthModal = document.getElementById('ftth-modal');
    const ftthDialog = ftthModal?.querySelector('.ftth-dialog');
    const ftthModalClose = document.getElementById('ftth-modal-close');
    const ftthMainFrame = document.getElementById('ftth-grafana-main');
    const ftthPowerFrame = document.getElementById('ftth-grafana-power');
    const ftthCrcFrame = document.getElementById('ftth-grafana-crc');
    const ftthPowerCard = document.getElementById('ftth-power-card');
    const ftthCrcCard = document.getElementById('ftth-crc-card');
    const ftthPowerToggle = document.getElementById('ftth-toggle-power');
    const ftthCrcToggle = document.getElementById('ftth-toggle-crc');

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

    function ftthGrafanaUrl(row, panelId) {
        const url = new URL(
            'http://127.0.0.1:8002/d-solo/adqfqpc/olt'
        );

        url.searchParams.set('orgId', '1');
        url.searchParams.set('from', `now-${ftthSelectedDays}d`);
        url.searchParams.set('to', 'now');
        url.searchParams.set('timezone', 'browser');
        url.searchParams.set('var-OLT', row.equipo);
        url.searchParams.set('var-PUERTO', '$__all');
        url.searchParams.set('var-SLOT', '$__all');
        url.searchParams.set('refresh', '5m');
        url.searchParams.set('panelId', panelId);
        url.searchParams.set('theme', 'light');

        return url.toString();
    }

    function loadFtthFrame(frame, panelId) {
        if (!frame || !ftthSelectedRow) {
            return;
        }

        const loading = frame.parentElement?.querySelector('.ftth-loading');

        if (loading) {
            loading.hidden = false;
            loading.textContent = 'Cargando gráfica…';
        }

        frame.src = ftthGrafanaUrl(ftthSelectedRow, panelId);
    }

    function resetFtthToggle(button, active) {
        button?.classList.toggle('is-active', active);
        button?.setAttribute('aria-pressed', String(active));
    }

    function setFtthRange(days) {
        ftthSelectedDays = days;

        ftthModal?.querySelectorAll('[data-ftth-days]').forEach((button) => {
            const active = Number(button.dataset.ftthDays) === days;
            button.classList.toggle('is-active', active);
            button.setAttribute('aria-pressed', String(active));
        });

        loadFtthFrame(ftthMainFrame, 'panel-1');

        if (ftthPowerVisible) {
            loadFtthFrame(ftthPowerFrame, 'panel-2');
        }

        if (ftthCrcVisible) {
            loadFtthFrame(ftthCrcFrame, 'panel-3');
        }
    }

    function openFtthModal(row, trigger) {
        ftthSelectedRow = row;
        ftthSelectedDays = 1;
        ftthPowerVisible = false;
        ftthCrcVisible = false;
        ftthReturnFocus = trigger;

        setText('ftth-modal-olt', row.equipo);
        ftthPowerCard.hidden = true;
        ftthCrcCard.hidden = true;
        ftthPowerFrame.removeAttribute('src');
        ftthCrcFrame.removeAttribute('src');
        resetFtthToggle(ftthPowerToggle, false);
        resetFtthToggle(ftthCrcToggle, false);
        ftthModal.hidden = false;
        document.body.classList.add('ftth-modal-open');
        app?.setAttribute('inert', '');
        setFtthRange(1);
        ftthModalClose?.focus();
    }

    function closeFtthModal() {
        if (!ftthModal || ftthModal.hidden) {
            return;
        }

        ftthModal.hidden = true;
        [ftthMainFrame, ftthPowerFrame, ftthCrcFrame].forEach((frame) => {
            frame?.removeAttribute('src');
        });
        ftthSelectedRow = null;
        ftthSelectedDays = 1;
        ftthPowerVisible = false;
        ftthCrcVisible = false;
        ftthPowerCard.hidden = true;
        ftthCrcCard.hidden = true;
        resetFtthToggle(ftthPowerToggle, false);
        resetFtthToggle(ftthCrcToggle, false);
        document.body.classList.remove('ftth-modal-open');
        app?.removeAttribute('inert');
        if (ftthReturnFocus?.isConnected) {
            ftthReturnFocus.focus();
        } else if (ftthReturnFocus) {
            const label = ftthReturnFocus.getAttribute('aria-label');
            [...document.querySelectorAll('.ftth-eye-button')]
                .find((button) => button.getAttribute('aria-label') === label)
                ?.focus();
        }
        ftthReturnFocus = null;
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

            const stateActions = document.createElement('div');
            const eyeButton = document.createElement('button');

            stateActions.className = 'gkp-state-actions';
            eyeButton.className = 'ftth-eye-button';
            eyeButton.type = 'button';
            eyeButton.title = 'Ver detalle OLT';
            eyeButton.setAttribute('aria-label', `Ver detalle de ${row.equipo}`);
            eyeButton.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z"/><circle cx="12" cy="12" r="2.5"/></svg>';
            eyeButton.addEventListener('click', () => openFtthModal(row, eyeButton));

            stateActions.append(badge, eyeButton);
            state.append(stateActions);

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

    ftthModalClose?.addEventListener('click', closeFtthModal);
    ftthModal?.querySelector('[data-ftth-close]')?.addEventListener('click', closeFtthModal);

    ftthModal?.querySelectorAll('[data-ftth-days]').forEach((button) => {
        button.addEventListener('click', () => setFtthRange(Number(button.dataset.ftthDays)));
    });

    ftthPowerToggle?.addEventListener('click', () => {
        ftthPowerVisible = !ftthPowerVisible;
        ftthPowerCard.hidden = !ftthPowerVisible;
        resetFtthToggle(ftthPowerToggle, ftthPowerVisible);

        if (ftthPowerVisible) {
            loadFtthFrame(ftthPowerFrame, 'panel-2');
        } else {
            ftthPowerFrame.removeAttribute('src');
        }
    });

    ftthCrcToggle?.addEventListener('click', () => {
        ftthCrcVisible = !ftthCrcVisible;
        ftthCrcCard.hidden = !ftthCrcVisible;
        resetFtthToggle(ftthCrcToggle, ftthCrcVisible);

        if (ftthCrcVisible) {
            loadFtthFrame(ftthCrcFrame, 'panel-3');
        } else {
            ftthCrcFrame.removeAttribute('src');
        }
    });

    [ftthMainFrame, ftthPowerFrame, ftthCrcFrame].forEach((frame) => {
        frame?.addEventListener('load', () => {
            const loading = frame.parentElement?.querySelector('.ftth-loading');
            if (loading) loading.hidden = true;
        });
        frame?.addEventListener('error', () => {
            const loading = frame.parentElement?.querySelector('.ftth-loading');
            if (loading) loading.textContent = 'No se pudo cargar la gráfica.';
        });
    });

    document.addEventListener('keydown', (event) => {
        if (!ftthModal || ftthModal.hidden) return;

        if (event.key === 'Escape') {
            event.preventDefault();
            closeFtthModal();
            return;
        }

        if (event.key !== 'Tab') return;

        const focusable = [...ftthDialog.querySelectorAll(
            'button:not([disabled]), iframe[src], [href], [tabindex]:not([tabindex="-1"])'
        )].filter((element) => !element.closest('[hidden]'));
        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first?.focus();
        }
    });

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
