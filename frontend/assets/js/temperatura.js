(() => {
    'use strict';

    const panel = document.getElementById('temperatura-panel');
    const rows = document.getElementById('temperatura-rows');
    const status = document.getElementById('temperatura-status');
    const updated = document.getElementById('temperatura-updated');
    const number = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 2 });
    let busy = false;

    function temperatureState(value) {
        // Estado provisional hasta confirmar los umbrales operativos.
        return 'Normal';
    }

    async function loadTemperature() {
        if (busy) return;
        busy = true;
        panel.setAttribute('aria-busy', 'true');
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 20000);
        try {
            const response = await fetch('../backend/api/temperatura.php', {
                cache: 'no-store',
                signal: controller.signal
            });
            if (!response.ok) throw new Error('HTTP inválido');
            const payload = await response.json();
            if (payload.ok !== true || !Array.isArray(payload.data?.temperaturas)) {
                throw new Error('Respuesta inválida');
            }
            const fragment = document.createDocumentFragment();
            for (const item of payload.data.temperaturas) {
                if (typeof item.temperatura !== 'number' || !Number.isFinite(item.temperatura)) {
                    throw new Error('Temperatura inválida');
                }
                const row = document.createElement('tr');
                for (const value of [item.equipo, 'N/D', `${number.format(item.temperatura)} °C`, temperatureState(item.temperatura)]) {
                    const cell = document.createElement('td');
                    cell.textContent = value;
                    row.appendChild(cell);
                }
                row.firstElementChild.title = `Tarjeta: ${item.tarjeta}`;
                fragment.appendChild(row);
            }
            rows.replaceChildren(fragment);
            status.textContent = payload.data.temperaturas.length ? '' : 'Sin lecturas de temperatura en los últimos 10 minutos.';
            updated.textContent = `Última actualización: ${new Date().toLocaleString('es-CO')}`;
        } catch (error) {
            rows.replaceChildren();
            status.textContent = 'No se pudo consultar la temperatura OLT. Se reintentará automáticamente.';
        } finally {
            clearTimeout(timeout);
            busy = false;
            panel.setAttribute('aria-busy', 'false');
        }
    }

    document.getElementById('gkp-refresh').addEventListener('click', loadTemperature);
    loadTemperature();
    setInterval(loadTemperature, 30000);
})();
