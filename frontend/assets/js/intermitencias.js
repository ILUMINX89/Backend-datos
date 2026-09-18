(() => {
    'use strict';

    const crearCelda = (valor) => {
        const td = document.createElement('td');
        td.textContent = valor === null || valor === undefined || valor === ''
            ? '—'
            : String(valor);
        return td;
    };

    const crearPanel = ({
        prefijo,
        endpoint,
        clave,
        mensajeVacio,
        etiquetaSingular,
        etiquetaPlural,
        crearFilas,
    }) => {
        const panel = document.getElementById(`${prefijo}-panel`);
        const rows = document.getElementById(`${prefijo}-rows`);
        const status = document.getElementById(`${prefijo}-status`);
        const table = document.getElementById(`${prefijo}-table`);
        const summary = document.getElementById(`${prefijo}-summary`);
        const refresh = document.getElementById(`${prefijo}-refresh`);

        if (!panel || !rows || !status || !table || !summary || !refresh) {
            return null;
        }

        let busy = false;

        const mostrarEstado = (mensaje, resumen) => {
            rows.replaceChildren();
            table.hidden = true;
            status.style.display = '';
            status.textContent = mensaje;
            summary.textContent = resumen;
        };

        const render = (items) => {
            rows.replaceChildren();

            if (!items.length) {
                mostrarEstado(mensajeVacio, `0 ${etiquetaPlural}`);
                return;
            }

            const fragment = document.createDocumentFragment();
            crearFilas(items).forEach((tr) => fragment.appendChild(tr));
            rows.appendChild(fragment);

            table.hidden = false;
            status.style.display = 'none';
            status.textContent = '';
            summary.textContent = items.length === 1
                ? `1 ${etiquetaSingular}`
                : `${items.length} ${etiquetaPlural}`;
        };

        const load = async () => {
            if (busy) {
                return;
            }

            busy = true;
            refresh.disabled = true;
            panel.setAttribute('aria-busy', 'true');
            mostrarEstado('Cargando…', 'Consultando información disponible…');

            try {
                const response = await fetch(endpoint, { cache: 'no-store' });
                const payload = await response.json();
                const items = payload.data?.[clave];

                if (!response.ok || payload.ok !== true || !Array.isArray(items)) {
                    throw new Error('Respuesta inválida del servicio');
                }

                render(items);
            } catch (error) {
                console.error(`Error consultando ${etiquetaPlural}:`, error);
                mostrarEstado(
                    'No se pudo consultar la información. Intente actualizar nuevamente.',
                    'Error de consulta'
                );
            } finally {
                busy = false;
                refresh.disabled = false;
                panel.setAttribute('aria-busy', 'false');
            }
        };

        refresh.addEventListener('click', load);
        return { load };
    };

    const intermitencias = crearPanel({
        prefijo: 'intermitencias',
        endpoint: '../backend/api/intermitencias.php',
        clave: 'intermitencias',
        mensajeVacio: 'No se detectaron puertos intermitentes.',
        etiquetaSingular: 'puerto intermitente detectado',
        etiquetaPlural: 'puertos intermitentes detectados',
        crearFilas: (items) => items.map((item) => {
            const tr = document.createElement('tr');
            tr.append(
                crearCelda(item.cmts),
                crearCelda(item.puerto),
                crearCelda(item.descripcion),
                crearCelda(item.cantidad_intermitencias),
                crearCelda(item.estado)
            );
            return tr;
        }),
    });

    const duplicados = crearPanel({
        prefijo: 'duplicados',
        endpoint: '../backend/api/puertos_duplicados.php',
        clave: 'puertos_duplicados',
        mensajeVacio: 'No se detectaron nodos asociados a múltiples puertos.',
        etiquetaSingular: 'nodo duplicado detectado',
        etiquetaPlural: 'nodos duplicados detectados',
        crearFilas: (items) => items.flatMap((item) => {
            const ubicaciones = Array.isArray(item.ubicaciones)
                ? item.ubicaciones
                : [];

            return ubicaciones.map((ubicacion) => {
                const tr = document.createElement('tr');
                tr.append(
                    crearCelda(item.nodo),
                    crearCelda(item.cantidad_ubicaciones),
                    crearCelda(ubicacion.cmts),
                    crearCelda(ubicacion.puerto)
                );
                return tr;
            });
        }),
    });

    intermitencias?.load();
    duplicados?.load();
})();
