(() => {
    const API = '/backend/api';
    const $ = selector => document.querySelector(selector);
    const text = (selector, value) => { const element = $(selector); if (element) element.textContent = String(value ?? ''); };

    function cell(row, value, className = '') {
        const td = document.createElement('td');
        td.textContent = value == null ? '--' : String(value);
        if (className) td.className = className;
        row.append(td);
        return td;
    }
    function renderAlarms(alarms) {
        const body = $('#tabla-alarmas tbody');
        body.replaceChildren();
        alarms.forEach(alarm => {
            const row = document.createElement('tr');
            row.dataset.tipo = String(alarm.tipo);
            row.dataset.estado = String(alarm.estado).toUpperCase();
            cell(row, new Date(alarm.fecha_hora).toLocaleString('es-CO'));
            const typeCell = cell(row, '');
            const badge = document.createElement('span');
            badge.className = `tipo tipo-${alarm.tipo}`;
            badge.textContent = `Tipo ${alarm.tipo}`;
            typeCell.append(badge);
            cell(row, alarm.estado); cell(row, alarm.olt); cell(row, alarm.puerto);
            cell(row, alarm.descripcion); cell(row, alarm.sitio); cell(row, alarm.valor);
            const actionCell = cell(row, '');
            const button = document.createElement('button');
            button.className = 'action'; button.type = 'button'; button.textContent = 'Reconocer';
            button.addEventListener('click', () => acknowledge(alarm.id));
            actionCell.append(button); body.append(row);
        });
        window.NocTable?.applyFilters();
    }
    async function acknowledge(id) {
        const response = await fetch(`${API}/reconocer.php`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({id, usuario: 'admin'})});
        if (!response.ok) throw new Error('No fue posible reconocer la alarma');
        await loadDashboard();
    }
    function render(data) {
        const summary = data.resumen ?? {};
        ['total', 'tipo1', 'tipo2', 'tipo3'].forEach(key => text(`#${key}`, summary[key] ?? 0));
        text('#sidebar-total', summary.total ?? 0);
        renderAlarms(data.alarmas ?? []);
        const top = $('#top-list'); top.replaceChildren();
        (data.top ?? []).forEach(item => { const li = document.createElement('li'); li.textContent = `${item.equipo}: ${item.total}`; top.append(li); });
        text('#tendencia', `${(data.tendencia ?? []).length} puntos recibidos`);
        window.dispatchEvent(new CustomEvent('dashboard:update', {detail: data}));
    }
    async function loadDashboard() {
        try {
            const response = await fetch(`${API}/dashboard.php`, {headers: {'Accept': 'application/json'}, cache: 'no-store'});
            const payload = await response.json();
            if (!response.ok || !payload.ok) throw new Error(payload.error ?? 'Error al cargar');
            render(payload.data); $('#error-state').hidden = true;
            $('#service-dot').className = 'dot online'; text('#service-status', 'Tiempo real');
            text('#last-update', `Actualizado: ${new Date().toLocaleTimeString('es-CO')}`);
        } catch (error) {
            $('#error-state').hidden = false; $('#service-dot').className = 'dot offline'; text('#service-status', 'Sin conexión');
        }
    }
    function updateClock() { text('#clock', new Date().toLocaleString('es-CO')); }
    updateClock(); setInterval(updateClock, 1000); loadDashboard(); setInterval(loadDashboard, 5000);
})();
