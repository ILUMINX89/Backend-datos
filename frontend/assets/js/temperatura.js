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

            equipo.title =
                `Tarjeta: ${item.tarjeta || 'N/D'}`;

            /*
             * ZONA
             */
            const zona =
                document.createElement('td');

            zona.textContent =
                item.zona || 'N/D';

            /*
             * TEMPERATURA
             */
            const valor =
                document.createElement('td');

            valor.textContent =
                formatTemperature(
                    temperatura
                );

            /*
             * ESTADO
             */
            const estado =
                document.createElement('td');

            const badge =
                document.createElement('span');

            badge.textContent =
                item.estado || 'Advertencia';

            badge.className =
                `temperature-badge ${badgeClass(item.nivel || 'amarillo')}`;

            estado.appendChild(badge);

            row.append(
                equipo,
                zona,
                valor,
                estado
            );

            fragment.appendChild(row);
        }

        rows.replaceChildren(fragment);

        tableRegion.hidden = visibleCount === 0;
        empty.hidden = visibleCount !== 0;
        count.textContent = String(visibleCount);

        return visibleCount;
    }

    async function loadTemperature() {
        if (busy) {
            return;
        }

        busy = true;

        panel.setAttribute(
            'aria-busy',
            'true'
        );

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

            status.textContent = '';

            updated.textContent =
                'Última actualización: ' +
                new Date().toLocaleString(
                    'es-CO'
                );
        } catch (error) {
            rows.replaceChildren();

            tableRegion.hidden = false;
            empty.hidden = true;
            count.textContent = '—';

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
            loadTemperature
        );
    }

    loadTemperature();

    setInterval(
        loadTemperature,
        30000
    );
})();
