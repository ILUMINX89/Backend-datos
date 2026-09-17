(() => {
    'use strict';

    const panel = document.getElementById(
        'temperatura-panel'
    );

    const rows = document.getElementById(
        'temperatura-rows'
    );

    const status = document.getElementById(
        'temperatura-status'
    );

    const updated = document.getElementById(
        'temperatura-updated'
    );

    const tableRegion = document.getElementById(
        'temperatura-table-region'
    );

    const empty = document.getElementById(
        'temperatura-empty'
    );

    const count = document.getElementById(
        'temperatura-count'
    );

    let busy = false;
    let hasValidData = false;
    let selectedTemperatureItem = null;
    let selectedTemperatureDays = 1;
    let temperatureReturnFocus = null;

    const app = document.querySelector('.app');
    const temperatureModal = document.getElementById('temperature-detail-modal');
    const temperatureDialog = temperatureModal?.querySelector('.temperature-detail-dialog');
    const temperatureClose = document.getElementById('temperature-detail-close');
    const temperatureIframe = document.getElementById('temperature-grafana');
    const temperatureLoading = document.getElementById('temperature-chart-loading');
    const temperatureChartTitle = document.getElementById('temperature-chart-title');

    function formatTemperature(value) {
        const temperatura = Number(value);

        if (!Number.isFinite(temperatura)) {
            return 'N/D';
        }

        return `${temperatura.toFixed(2)} °C`;
    }

    function badgeClass(nivel) {
        if (nivel === 'rojo') {
            return 'temperature-badge--red';
        }

        if (nivel === 'naranja') {
            return 'temperature-badge--orange';
        }

        return 'temperature-badge--yellow';
    }

    function temperatureGrafanaUrl(item) {
        const url = new URL(
            'http://127.0.0.1:8002/d-solo/adqfqpc/olt'
        );

        url.searchParams.set('orgId', '1');
        url.searchParams.set('from', `now-${selectedTemperatureDays}d`);
        url.searchParams.set('to', 'now');
        url.searchParams.set('timezone', 'browser');
        url.searchParams.set('var-OLT', item.equipo);
        url.searchParams.set('var-PUERTO', '$__all');
        url.searchParams.set('var-SLOT', '$__all');
        url.searchParams.set('refresh', '5m');
        url.searchParams.set('panelId', 'panel-4');
        url.searchParams.set('theme', 'light');

        return url.toString();
    }

    function temperatureLevelLabel(nivel) {
        if (nivel === 'rojo') return 'Crítica';
        if (nivel === 'naranja') return 'Alta';
        return 'Elevada';
    }

    function temperatureRangeTitle(days) {
        if (days === 1) return 'Temperatura · último día';
        return `Temperatura · últimos ${days} días`;
    }

    function loadTemperatureChart() {
        if (!temperatureIframe || !selectedTemperatureItem) return;

        temperatureLoading.hidden = false;
        temperatureLoading.textContent = 'Cargando gráfica…';
        temperatureIframe.src = temperatureGrafanaUrl(selectedTemperatureItem);
    }

    function setTemperatureRange(days, { reload = true } = {}) {
        selectedTemperatureDays = days;

        temperatureModal?.querySelectorAll('[data-temperature-days]').forEach((button) => {
            const active = Number(button.dataset.temperatureDays) === days;
            button.classList.toggle('is-active', active);
            button.setAttribute('aria-pressed', String(active));
        });

        temperatureChartTitle.textContent = temperatureRangeTitle(days);

        if (reload) loadTemperatureChart();
    }

    function openTemperatureModal(item, trigger) {
        selectedTemperatureItem = item;
        selectedTemperatureDays = 1;
        temperatureReturnFocus = trigger;

        const nivel = item.nivel || 'amarillo';
        const current = document.getElementById('temperature-detail-current');
        const level = document.getElementById('temperature-detail-level');

        document.getElementById('temperature-detail-olt').textContent = item.equipo || 'N/D';
        current.textContent = formatTemperature(item.temperatura);
        level.textContent = temperatureLevelLabel(nivel);
        current.className = `temperature-detail-value temperature-detail-value--${nivel}`;
        level.className = `temperature-detail-value temperature-detail-value--${nivel}`;
        temperatureModal.hidden = false;
        document.body.classList.add('temperature-detail-modal-open');
        app?.setAttribute('inert', '');
        setTemperatureRange(1);
        temperatureClose?.focus();
    }

    function closeTemperatureModal() {
        if (!temperatureModal || temperatureModal.hidden) return;

        temperatureModal.hidden = true;
        temperatureIframe.removeAttribute('src');
        selectedTemperatureItem = null;
        selectedTemperatureDays = 1;
        setTemperatureRange(1, { reload: false });
        document.body.classList.remove('temperature-detail-modal-open');
        app?.removeAttribute('inert');

        if (temperatureReturnFocus?.isConnected) {
            temperatureReturnFocus.focus();
        } else if (temperatureReturnFocus) {
            const label = temperatureReturnFocus.getAttribute('aria-label');
            [...document.querySelectorAll('.temperature-detail-button')]
                .find((button) => button.getAttribute('aria-label') === label)
                ?.focus();
        }

        temperatureReturnFocus = null;
    }

    function renderTemperature(
        temperatures
    ) {
        const fragment =
            document.createDocumentFragment();

        let visibleCount = 0;

        for (const item of temperatures) {
            const temperatura = Number(
                item.temperatura
            );

            if (
                !Number.isFinite(temperatura)
            ) {
                continue;
            }

            /*
             * Protección adicional:
             * no mostrar temperaturas normales.
             */
            if (temperatura < 70) {
                continue;
            }

            visibleCount += 1;

            const row =
                document.createElement('tr');

            /*
             * EQUIPO
             */
            const equipo =
                document.createElement('td');

            equipo.textContent =
                item.equipo || 'N/D';

            /*
             * TEMPERATURA
             */
            const valor =
                document.createElement('td');

            const badge =
                document.createElement('span');

            badge.textContent =
                formatTemperature(
                    temperatura
                );

            badge.className =
                `temperature-badge ${badgeClass(item.nivel || 'amarillo')}`;

            const actions = document.createElement('div');
            const detailButton = document.createElement('button');

            actions.className = 'temperature-cell-actions';
            detailButton.className = 'temperature-detail-button';
            detailButton.type = 'button';
            detailButton.title = 'Ver detalle de temperatura';
            detailButton.setAttribute(
                'aria-label',
                `Ver detalle de temperatura de ${item.equipo || 'N/D'}`
            );
            detailButton.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z"/><circle cx="12" cy="12" r="2.5"/></svg>';
            detailButton.addEventListener('click', () => openTemperatureModal(item, detailButton));
            actions.append(badge, detailButton);
            valor.appendChild(actions);

            row.append(
                equipo,
                valor
            );

            fragment.appendChild(row);
        }

        rows.replaceChildren(fragment);

        tableRegion.hidden = visibleCount === 0;
        empty.hidden = visibleCount !== 0;
        count.textContent = String(visibleCount);

        return visibleCount;
    }

    async function loadTemperature({ silent = false } = {}) {
        if (busy) {
            return;
        }

        busy = true;

        panel.setAttribute(
            'aria-busy',
            'true'
        );

        if (!silent && !hasValidData) {
            status.textContent = 'Consultando temperatura OLT…';
        }

        const controller =
            new AbortController();

        const timeout = setTimeout(
            () => controller.abort(),
            20000
        );

        try {
            const response = await fetch(
                '../backend/api/temperatura.php',
                {
                    cache: 'no-store',
                    signal: controller.signal,
                }
            );

            if (!response.ok) {
                throw new Error(
                    'HTTP inválido'
                );
            }

            const payload =
                await response.json();

            if (
                payload.ok !== true
                || !Array.isArray(
                    payload.data?.temperaturas
                )
            ) {
                throw new Error(
                    'Respuesta inválida'
                );
            }

            const temperaturas =
                payload.data.temperaturas;

            renderTemperature(
                temperaturas
            );
            hasValidData = true;

            status.textContent = '';

            updated.textContent =
                'Última actualización: ' +
                new Date().toLocaleString(
                    'es-CO'
                );
        } catch (error) {
            if (!hasValidData) {
                rows.replaceChildren();
                tableRegion.hidden = false;
                empty.hidden = true;
                count.textContent = '—';
            }

            status.textContent =
                'No se pudo consultar la ' +
                'temperatura OLT. Se reintentará ' +
                'automáticamente.';
        } finally {
            clearTimeout(timeout);

            busy = false;

            panel.setAttribute(
                'aria-busy',
                'false'
            );
        }
    }

    const refresh =
        document.getElementById(
            'gkp-refresh'
        );

    if (refresh) {
        refresh.addEventListener(
            'click',
            () => loadTemperature({ silent: false })
        );
    }

    temperatureClose?.addEventListener('click', closeTemperatureModal);
    temperatureModal?.querySelector('[data-temperature-modal-close]')
        ?.addEventListener('click', closeTemperatureModal);

    temperatureModal?.querySelectorAll('[data-temperature-days]').forEach((button) => {
        button.addEventListener('click', () => {
            setTemperatureRange(Number(button.dataset.temperatureDays));
        });
    });

    temperatureIframe?.addEventListener('load', () => {
        temperatureLoading.hidden = true;
    });

    temperatureIframe?.addEventListener('error', () => {
        temperatureLoading.hidden = false;
        temperatureLoading.textContent = 'No se pudo cargar la gráfica.';
    });

    document.addEventListener('keydown', (event) => {
        if (!temperatureModal || temperatureModal.hidden) return;

        if (event.key === 'Escape') {
            event.preventDefault();
            closeTemperatureModal();
            return;
        }

        if (event.key !== 'Tab') return;

        const focusable = [...temperatureDialog.querySelectorAll(
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

    loadTemperature();

    setInterval(
        () => loadTemperature({ silent: true }),
        30000
    );
})();
