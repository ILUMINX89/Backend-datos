(() => {
    'use strict';

    const body = document.getElementById('hfc-rows');
    const status = document.getElementById('hfc-status');
    const panel = document.getElementById('alarmas');
    const refresh = document.getElementById('hfc-refresh');
    const summary = document.getElementById('hfc-summary');
    const table = document.getElementById('hfc-table');
    const modal = document.getElementById('hfc-modal');
    const dialog = modal?.querySelector('.hfc-dialog');
    const closeButton = document.getElementById('hfc-modal-close');
    const grafana = document.getElementById('hfc-grafana');
    const app = document.querySelector('.app');
    const number = new Intl.NumberFormat('es-CO', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
    let busy = false;
    let updating = false;
    let statusTimer = null;
    let currentRows = [];
    let selectedRow = null;
    let returnFocus = null;
    let selectedDays = 3;
    let selectedPanel = 'panel-1';

    function grafanaUrl(row) {
        const url = new URL(
            'http://127.0.0.1:8002/d-solo/adsfhrn/cmts'
        );

        url.searchParams.set('orgId', '1');

        // Rango seleccionado con los botones 1D / 2D / 3D / 7D
        url.searchParams.set('from', `now-${selectedDays}d`);
        url.searchParams.set('to', 'now');

        url.searchParams.set('timezone', 'browser');

        // CMTS y nodo dinámicos
        url.searchParams.set('var-CMTS', row.equipo);
        url.searchParams.set('var-NODO', row.puerto);

        // En d-solo se usa panelId, no viewPanel
        url.searchParams.set('panelId', selectedPanel);

        // Tema claro
        url.searchParams.set('theme', 'light');

        return url.toString();
    }

    function portButton(row) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'hfc-port-option';
        button.classList.toggle('is-selected', row === selectedRow);
        button.setAttribute('aria-pressed', String(row === selectedRow));
        button.innerHTML = '<span></span><strong></strong>';
        button.querySelector('span').textContent = row.puerto;
        button.querySelector('strong').textContent = `${number.format(Number(row.valor))} %`;
        button.addEventListener('click', () => selectRow(row));
        return button;
    }

    function compareCriticality(a, b) {
        const byPoints = Number(b.puntos_sobre_90 ?? 0) - Number(a.puntos_sobre_90 ?? 0);
        return byPoints || (Number(b.valor) - Number(a.valor));
    }

    function renderRelated() {
        const related = currentRows
            .filter((row) => row.equipo === selectedRow.equipo)
            .sort(compareCriticality);
        [['uso', 'hfc-use-list', 'hfc-use-group'], ['degradacion', 'hfc-degradation-list', 'hfc-degradation-group']]
            .forEach(([type, listId, groupId]) => {
                const rows = related.filter((row) => row.tipo === type);
                const list = document.getElementById(listId);
                const group = document.getElementById(groupId);
                list.replaceChildren(...rows.map(portButton));
                group.hidden = rows.length === 0;
            });
    }

    function selectRow(row) {
        selectedRow = row;
        document.getElementById('hfc-modal-cmts').textContent = row.equipo;
        document.getElementById('hfc-modal-node').textContent = row.puerto;
        document.getElementById('hfc-modal-state').textContent = row.estado;
        document.getElementById('hfc-modal-value').textContent = `${number.format(Number(row.valor))} %`;
        grafana.src = grafanaUrl(row);
        grafana.title = `Gráfica Grafana de ${row.puerto} en ${row.equipo}, últimos 3 días`;
        renderRelated();
    }

    function openModal(row, trigger) {
        returnFocus = trigger;
        modal.hidden = false;
        app?.setAttribute('inert', '');
        document.body.classList.add('hfc-modal-open');
        selectRow(row);
        dialog.focus();
    }

    function closeModal() {
        if (modal.hidden) return;
        modal.hidden = true;
        app?.removeAttribute('inert');
        document.body.classList.remove('hfc-modal-open');
        grafana.removeAttribute('src');
        returnFocus?.focus();
    }

    function eyeButton(row) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'hfc-eye-button';
        button.title = 'Ver detalle';
        button.setAttribute('aria-label', `Ver detalle de ${row.puerto} en ${row.equipo}`);
        button.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z"/><circle cx="12" cy="12" r="2.5"/></svg>';
        button.addEventListener('click', () => openModal(row, button));
        return button;
    }

    function render(rows) {
        const fragment = document.createDocumentFragment();
        rows.forEach((row) => {
            const tr = document.createElement('tr');
            [row.equipo, row.puerto, `${number.format(Number(row.valor))} %`]
                .forEach((text) => {
                    const td = document.createElement('td');
                    td.textContent = text;
                    tr.append(td);
                });
            const state = document.createElement('td');
            const stateWrap = document.createElement('div');
            stateWrap.className = 'hfc-state';
            const badge = document.createElement('span');
            badge.className = `gkp-badge${row.tipo === 'degradacion' ? ' hfc-badge--degradation' : ''}`;
            badge.textContent = row.estado;
            badge.title = row.detalle || '';
            stateWrap.append(badge, eyeButton(row));
            state.append(stateWrap);
            tr.append(state);
            fragment.append(tr);
        });
        body.replaceChildren(fragment);
    }

    async function load() {
        if (busy) return;
        busy = true;
        refresh.disabled = true;
        panel.setAttribute('aria-busy', 'true');
        status.textContent = 'Cargando último estado HFC…';
        try {
            const endpoint = new URL('../backend/api/hfc.php', window.location.href);
            const response = await fetch(endpoint, { cache: 'no-store' });
            const payload = await response.json();
            const rows = payload.data?.estado_actual_hfc;
            if (!response.ok || !payload.ok || !Array.isArray(rows)) {
                throw new Error('Respuesta no disponible');
            }
            currentRows = [...rows].sort(compareCriticality);
            render(currentRows);
            table.hidden = currentRows.length === 0;
            summary.textContent = currentRows.length === 1
                ? '1 puerto requiere revisión'
                : `${currentRows.length} puertos requieren revisión`;
            status.textContent = !payload.data?.actualizado_en
                ? 'No hay datos HFC almacenados. Pulsa Actualizar para generar el primer estado.'
                : currentRows.length ? '' : 'Sin afectaciones CMTS confirmadas';
        } catch (_error) {
            status.textContent = 'No se pudo consultar el estado HFC.';
        } finally {
            busy = false;
            refresh.disabled = updating;
            panel.setAttribute('aria-busy', 'false');
        }
    }

    async function checkUpdateStatus() {
        try {
            const endpoint = new URL('../backend/api/hfc_estado.php', window.location.href);
            const response = await fetch(endpoint, { cache: 'no-store' });
            const payload = await response.json();
            if (!response.ok || !payload.ok) throw new Error('No se pudo consultar el estado HFC.');
            const state = payload.data?.estado;
            if (state === 'procesando') {
                statusTimer = window.setTimeout(checkUpdateStatus, 5000);
                return;
            }
            updating = false;
            refresh.disabled = false;
            if (state === 'listo') {
                await load();
            } else if (state === 'error') {
                status.textContent = payload.data?.error || 'Falló la actualización HFC; se conservan los últimos datos.';
            } else {
                throw new Error('Estado de actualización HFC no reconocido.');
            }
        } catch (error) {
            updating = false;
            refresh.disabled = false;
            status.textContent = error.message || 'No se pudo consultar el estado HFC.';
        }
    }

    async function startUpdate() {
        if (updating || busy) return;
        updating = true;
        refresh.disabled = true;
        status.textContent = 'Actualizando datos HFC de los últimos 4 días...';
        try {
            const endpoint = new URL('../backend/api/hfc_actualizar.php', window.location.href);
            const response = await fetch(endpoint, { method: 'POST', cache: 'no-store' });
            const payload = await response.json();
            if (!response.ok || !payload.ok || payload.estado !== 'procesando') {
                throw new Error(payload.error || 'No se pudo iniciar la actualización HFC.');
            }
            statusTimer = window.setTimeout(checkUpdateStatus, 5000);
        } catch (error) {
            updating = false;
            refresh.disabled = false;
            status.textContent = error.message || 'No se pudo iniciar la actualización HFC.';
        }
    }

    const rangeButtons = [
        ...document.querySelectorAll('.hfc-time-range button')
    ];

    const panelButtons = [
        ...document.querySelectorAll('.hfc-chart-switch button')
    ];

    const chartTitle = document.getElementById('hfc-chart-title');

    function changeDays(days) {
        selectedDays = Number(days);

        rangeButtons.forEach((button) => {
            const active = Number(button.dataset.days) === selectedDays;

            button.classList.toggle('is-active', active);
            button.setAttribute('aria-pressed', String(active));
        });

        if (chartTitle) {
            chartTitle.textContent = selectedDays === 1
                ? 'Gráfica último día'
                : `Gráfica últimos ${selectedDays} días`;
        }

        if (selectedRow) {
            grafana.src = grafanaUrl(selectedRow);
        }
    }
    function changePanel(panel) {
        selectedPanel = panel;

        panelButtons.forEach((button) => {
            const active = button.dataset.panel === selectedPanel;

            button.classList.toggle('is-active', active);
            button.setAttribute('aria-pressed', String(active));
        });

        if (selectedRow) {
            grafana.src = grafanaUrl(selectedRow);
        }
    }

    if (
        !body ||
        !status ||
        !panel ||
        !refresh ||
        !summary ||
        !table ||
        !modal ||
        !dialog ||
        !grafana
    ) return;

    rangeButtons.forEach((button) => {
        button.addEventListener('click', () => {
            changeDays(button.dataset.days);
        });
    });
    panelButtons.forEach((button) => {
        button.addEventListener('click', () => {
            changePanel(button.dataset.panel);
        });
    });

    refresh.addEventListener('click', startUpdate);
    closeButton.addEventListener('click', closeModal);
    modal.querySelector('[data-modal-close]').addEventListener('click', closeModal);
    document.addEventListener('keydown', (event) => {
        if (modal.hidden) return;
        if (event.key === 'Escape') closeModal();
        if (event.key === 'Tab') {
            const focusable = [...dialog.querySelectorAll('button:not([hidden]), iframe')];
            const first = focusable[0];
            const last = focusable[focusable.length - 1];
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        }
    });
    load();
})();

