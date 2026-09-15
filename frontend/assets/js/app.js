(() => {
    const API = '/backend/api';

    const $ = selector =>
        document.querySelector(selector);

    const text = (
        selector,
        value
    ) => {
        const element = $(
            selector
        );

        if (element) {
            element.textContent = String(
                value ?? ''
            );
        }
    };


    // ============================================================
    // CREAR CELDA
    // ============================================================

    function cell(
        row,
        value,
        className = ''
    ) {
        const td = document.createElement(
            'td'
        );

        td.textContent = (
            value == null
                ? '--'
                : String(value)
        );

        if (className) {
            td.className = (
                className
            );
        }

        row.append(
            td
        );

        return td;
    }


    // ============================================================
    // FORMATEAR FECHA
    // ============================================================

    function formatDate(
        value
    ) {
        if (!value) {
            return '--';
        }

        const date = new Date(
            value
        );

        if (
            Number.isNaN(
                date.getTime()
            )
        ) {
            return String(
                value
            );
        }

        return date.toLocaleString(
            'es-CO'
        );
    }


    // ============================================================
    // RENDER TABLA
    // ============================================================

    function renderAlarms(
        alarms
    ) {
        const body = $(
            '#tabla-alarmas tbody'
        );

        if (!body) {
            return;
        }

        body.replaceChildren();

        const emptyState = $(
            '#alarmas-vacias'
        );

        if (
            !Array.isArray(alarms) ||
            alarms.length === 0
        ) {
            if (emptyState) {
                emptyState.hidden = false;
            }

            return;
        }

        if (emptyState) {
            emptyState.hidden = true;
        }

        alarms.forEach(
            alarm => {
                const row = (
                    document.createElement(
                        'tr'
                    )
                );

                const tipo = Number(
                    alarm.tipo
                    ?? 0
                );

                const estado = String(
                    alarm.estado
                    ?? ''
                ).toUpperCase();

                const origen = String(
                    alarm.origen
                    ?? 'ALARMA'
                ).toUpperCase();


                // ================================================
                // DATASET PARA FILTROS
                // ================================================

                row.dataset.tipo = String(
                    tipo
                );

                row.dataset.estado = (
                    estado
                );

                row.dataset.origen = (
                    origen
                );


                // ================================================
                // RESALTAR INTERMITENCIAS
                // ================================================

                if (
                    origen
                    === 'INTERMITENCIA'
                ) {
                    row.classList.add(
                        'intermitencia'
                    );
                }


                // ================================================
                // HORA
                // ================================================

                cell(
                    row,
                    formatDate(
                        alarm.fecha_hora
                    )
                );


                // ================================================
                // SEVERIDAD
                // ================================================

                const typeCell = cell(
                    row,
                    ''
                );

                const badge = (
                    document.createElement(
                        'span'
                    )
                );

                badge.className = (
                    `tipo tipo-${tipo}`
                );

                badge.textContent = (
                    `Tipo ${tipo}`
                );

                typeCell.replaceChildren(
                    badge
                );


                // ================================================
                // ESTADO
                // ================================================

                cell(
                    row,
                    estado
                );


                // ================================================
                // OLT
                // ================================================

                cell(
                    row,
                    alarm.olt
                );


                // ================================================
                // PUERTO
                // ================================================

                cell(
                    row,
                    alarm.puerto
                );


                // ================================================
                // NODO / SITIO
                // ================================================
                //
                // El encabezado HTML tiene primero Sitio
                // y después Descripción.
                // ================================================

                cell(
                    row,
                    alarm.sitio
                );


                // ================================================
                // DESCRIPCIÓN
                // ================================================

                cell(
                    row,
                    alarm.descripcion
                );


                // ================================================
                // VALOR
                // ================================================

                cell(
                    row,
                    alarm.valor
                );


                // ================================================
                // ACCIONES
                // ================================================

                const actionCell = cell(
                    row,
                    ''
                );

                if (
                    origen
                    === 'INTERMITENCIA'
                ) {
                    // Las intermitencias todavía no son registros
                    // persistidos en MySQL, por lo tanto no se
                    // pueden reconocer mediante reconocer.php.

                    const indicator = (
                        document.createElement(
                            'span'
                        )
                    );

                    indicator.className = (
                        'action-status'
                    );

                    indicator.textContent = (
                        'Detectada'
                    );

                    actionCell.replaceChildren(
                        indicator
                    );

                } else {
                    const button = (
                        document.createElement(
                            'button'
                        )
                    );

                    button.className = (
                        'action'
                    );

                    button.type = (
                        'button'
                    );

                    button.textContent = (
                        'Reconocer'
                    );

                    button.addEventListener(
                        'click',
                        () => acknowledge(
                            alarm.id
                        )
                    );

                    actionCell.replaceChildren(
                        button
                    );
                }


                body.append(
                    row
                );
            }
        );

        window.NocTable
            ?.applyFilters();
    }


    // ============================================================
    // RECONOCER ALARMA MYSQL
    // ============================================================

    async function acknowledge(
        id
    ) {
        const response = await fetch(
            `${API}/reconocer.php`,
            {
                method: 'POST',

                headers: {
                    'Content-Type':
                        'application/json'
                },

                body: JSON.stringify({
                    id,
                    usuario: 'admin'
                })
            }
        );

        if (
            !response.ok
        ) {
            throw new Error(
                'No fue posible reconocer la alarma'
            );
        }

        await loadDashboard();
    }


    // ============================================================
    // RENDER GENERAL
    // ============================================================

    function render(
        data
    ) {
        const summary = (
            data.resumen
            ?? {}
        );

        [
            'total',
            'tipo1',
            'tipo2',
            'tipo3'
        ].forEach(
            key => {
                text(
                    `#${key}`,
                    summary[key]
                    ?? 0
                );
            }
        );


        // Sidebar
        text(
            '#sidebar-total',
            summary.total
            ?? 0
        );


        // Tabla de alarmas + intermitencias
        renderAlarms(
            data.alarmas
            ?? []
        );


        // ================================================
        // TOP OLT
        // ================================================

        const top = $(
            '#top-list'
        );

        if (top) {
            top.replaceChildren();

            (
                data.top
                ?? []
            ).forEach(
                item => {
                    const li = (
                        document.createElement(
                            'li'
                        )
                    );

                    li.textContent = (
                        `${item.equipo}: ${item.total}`
                    );

                    top.append(
                        li
                    );
                }
            );
        }


        // ================================================
        // TENDENCIA
        // ================================================

        text(
            '#tendencia',
            `${(
                data.tendencia
                ?? []
            ).length
            } puntos recibidos`
        );


        // ================================================
        // EVENTO PARA alarmas.js
        // ================================================

        window.dispatchEvent(
            new CustomEvent(
                'dashboard:update',
                {
                    detail: data
                }
            )
        );
    }


    // ============================================================
    // CARGAR DASHBOARD
    // ============================================================

    async function loadDashboard() {
        try {
            const response = await fetch(
                `${API}/dashboard.php`,
                {
                    headers: {
                        'Accept':
                            'application/json'
                    },

                    cache:
                        'no-store'
                }
            );

            const payload = (
                await response.json()
            );

            if (
                !response.ok ||
                !payload.ok
            ) {
                throw new Error(
                    payload.error
                    ?? 'Error al cargar'
                );
            }

            render(
                payload.data
            );


            // ================================================
            // ESTADO CONEXIÓN
            // ================================================

            const errorState = $(
                '#error-state'
            );

            if (errorState) {
                errorState.hidden = true;
            }

            const serviceDot = $(
                '#service-dot'
            );

            if (serviceDot) {
                serviceDot.className = (
                    'dot online'
                );
            }

            text(
                '#service-status',
                'Tiempo real'
            );

            text(
                '#last-update',
                `Actualizado: ${new Date()
                    .toLocaleTimeString(
                        'es-CO'
                    )
                }`
            );

        } catch (error) {
            console.error(
                'Error cargando dashboard:',
                error
            );

            const errorState = $(
                '#error-state'
            );

            if (errorState) {
                errorState.hidden = false;
            }

            const serviceDot = $(
                '#service-dot'
            );

            if (serviceDot) {
                serviceDot.className = (
                    'dot offline'
                );
            }

            text(
                '#service-status',
                'Sin conexión'
            );
        }
    }


    // ============================================================
    // RELOJ
    // ============================================================

    function updateClock() {
        text(
            '#clock',
            new Date()
                .toLocaleString(
                    'es-CO'
                )
        );
    }


    // ============================================================
    // INICIO
    // ============================================================

    updateClock();

    setInterval(
        updateClock,
        1000
    );

    loadDashboard();

    setInterval(
        loadDashboard,
        5000
    );
})();