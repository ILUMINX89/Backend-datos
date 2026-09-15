<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/bootstrap.php';

requireMethod('GET');

try {
    $client = alarmasClient();

    // ============================================================
    // 1. ALARMAS NORMALES
    // ============================================================

    $responseAlarmas = $client->get('/alarmas', [
        'limit' => 1000,
    ]);

    if (
        $responseAlarmas['status'] < 200 ||
        $responseAlarmas['status'] >= 300 ||
        !($responseAlarmas['body']['ok'] ?? false)
    ) {
        throw new RuntimeException(
            'Fallo la consulta de alarmas'
        );
    }

    $alarmas = (
        $responseAlarmas['body']['data']
        ?? []
    );

    // Marcamos origen para distinguirlas de las
    // intermitencias generadas automáticamente.
    foreach ($alarmas as &$alarma) {
        $alarma['origen'] = (
            $alarma['origen']
            ?? 'ALARMA'
        );
    }

    unset($alarma);


    // ============================================================
    // 2. INTERMITENCIAS OLT
    // ============================================================
    //
    // Por ahora usamos 7 días.
    //
    // El microservicio solamente devuelve un puerto cuando
    // tiene más de 2 caídas dentro del mismo día.
    // ============================================================

    $intermitenciasTabla = [];

    try {
        $responseIntermitencias = $client->get(
            '/api/olt/intermitencias',
            [
                'dias' => 2,
            ]
        );

        if (
            $responseIntermitencias['status'] >= 200 &&
            $responseIntermitencias['status'] < 300 &&
            ($responseIntermitencias['body']['ok'] ?? false)
        ) {
            $intermitencias = (
                $responseIntermitencias['body']['data']['datos']
                ?? []
            );

            foreach ($intermitencias as $grupoOlt) {
                $olt = (string) (
                    $grupoOlt['olt']
                    ?? ''
                );

                $puertos = (
                    $grupoOlt['puertos']
                    ?? []
                );

                foreach ($puertos as $puertoInfo) {
                    $puerto = (string) (
                        $puertoInfo['puerto']
                        ?? ''
                    );

                    $diasIntermitentes = (
                        $puertoInfo['dias']
                        ?? []
                    );

                    foreach (
                        $diasIntermitentes
                        as $diaInfo
                    ) {
                        $dia = (string) (
                            $diaInfo['dia']
                            ?? ''
                        );

                        $cantidadCaidas = (int) (
                            $diaInfo['cantidad_caidas']
                            ?? 0
                        );

                        $tiempoMinutos = (float) (
                            $diaInfo[
                                'tiempo_total_caido_minutos'
                            ]
                            ?? 0
                        );

                        $eventos = (
                            $diaInfo['eventos']
                            ?? []
                        );

                        // ====================================================
                        // FECHA PARA MOSTRAR EN LA TABLA
                        // ====================================================
                        //
                        // Tomamos el inicio del evento más reciente
                        // de ese día.
                        // ====================================================

                        $fechaHora = null;

                        if (!empty($eventos)) {
                            $ultimoEvento = end(
                                $eventos
                            );

                            if (
                                is_array($ultimoEvento)
                            ) {
                                $fechaHora = (
                                    $ultimoEvento['inicio']
                                    ?? null
                                );
                            }

                            reset($eventos);
                        }

                        // Si por algún motivo no existe inicio,
                        // usamos el día como referencia.
                        if (
                            $fechaHora === null ||
                            $fechaHora === ''
                        ) {
                            $fechaHora = (
                                $dia !== ''
                                ? $dia . 'T00:00:00'
                                : date('c')
                            );
                        }

                        // ====================================================
                        // ID VIRTUAL
                        // ====================================================
                        //
                        // No existe en MySQL.
                        // Solo sirve para identificar la fila en frontend.
                        // ====================================================

                        $idVirtual = sprintf(
                            'intermitencia-%s-%s-%s',
                            $olt,
                            str_replace(
                                '/',
                                '-',
                                $puerto
                            ),
                            $dia
                        );

                        $descripcion = sprintf(
                            'Puerto intermitente: %d caídas detectadas durante el día',
                            $cantidadCaidas
                        );

                        $valor = sprintf(
                            '%d caídas / %.2f min',
                            $cantidadCaidas,
                            $tiempoMinutos
                        );

                        $intermitenciasTabla[] = [
                            'id' => $idVirtual,
                            'fecha_hora' => $fechaHora,

                            // Inicialmente la clasificamos
                            // como severidad Tipo 2.
                            'tipo' => 2,

                            'estado' => 'ACTIVA',
                            'olt' => $olt,
                            'puerto' => $puerto,

                            'sitio' => 'Intermitencia OLT',

                            'descripcion' => $descripcion,

                            'valor' => $valor,

                            'origen' => 'INTERMITENCIA',

                            'dia_intermitencia' => $dia,

                            'cantidad_caidas' => (
                                $cantidadCaidas
                            ),

                            'tiempo_total_caido_minutos' => (
                                round(
                                    $tiempoMinutos,
                                    2
                                )
                            ),
                        ];
                    }
                }
            }
        }

    } catch (Throwable $exception) {
        // La falla de intermitencias no debe tumbar
        // todo el dashboard.
        error_log(
            'Intermitencias: '
            . $exception->getMessage()
        );
    }


    // ============================================================
    // 3. UNIFICAR ALARMAS + INTERMITENCIAS
    // ============================================================

    $eventosTabla = array_merge(
        $alarmas,
        $intermitenciasTabla
    );


    // ============================================================
    // 4. ORDENAR POR FECHA MÁS RECIENTE
    // ============================================================

    usort(
        $eventosTabla,
        static function (
            array $a,
            array $b
        ): int {
            $fechaA = strtotime(
                (string) (
                    $a['fecha_hora']
                    ?? ''
                )
            );

            $fechaB = strtotime(
                (string) (
                    $b['fecha_hora']
                    ?? ''
                )
            );

            $fechaA = (
                $fechaA === false
                ? 0
                : $fechaA
            );

            $fechaB = (
                $fechaB === false
                ? 0
                : $fechaB
            );

            return $fechaB <=> $fechaA;
        }
    );


    // ============================================================
    // 5. RESUMEN
    // ============================================================

    $resumen = [
        'total' => 0,
        'tipo1' => 0,
        'tipo2' => 0,
        'tipo3' => 0,
        'intermitencias' => 0,
    ];

    foreach (
        $eventosTabla
        as $evento
    ) {
        if (
            ($evento['estado'] ?? '')
            !== 'ACTIVA'
        ) {
            continue;
        }

        $resumen['total']++;

        $tipo = (int) (
            $evento['tipo']
            ?? 0
        );

        if ($tipo === 1) {
            $resumen['tipo1']++;

        } elseif ($tipo === 2) {
            $resumen['tipo2']++;

        } elseif ($tipo === 3) {
            $resumen['tipo3']++;
        }

        if (
            ($evento['origen'] ?? '')
            === 'INTERMITENCIA'
        ) {
            $resumen[
                'intermitencias'
            ]++;
        }
    }


    // ============================================================
    // 6. TOP POR OLT
    // ============================================================

    $conteoOlts = [];

    foreach (
        $eventosTabla
        as $evento
    ) {
        $olt = (string) (
            $evento['olt']
            ?? ''
        );

        if ($olt === '') {
            continue;
        }

        if (
            !isset(
                $conteoOlts[$olt]
            )
        ) {
            $conteoOlts[
                $olt
            ] = 0;
        }

        $conteoOlts[
            $olt
        ]++;
    }

    arsort(
        $conteoOlts
    );

    $top = [];

    foreach (
        array_slice(
            $conteoOlts,
            0,
            5,
            true
        )
        as $equipo => $total
    ) {
        $top[] = [
            'equipo' => $equipo,
            'total' => $total,
        ];
    }


    // ============================================================
    // 7. TENDENCIA
    // ============================================================
    //
    // Todavía no implementada.
    // ============================================================

    $tendencia = [];


    // ============================================================
    // RESPUESTA
    // ============================================================

    jsonResponse([
        'ok' => true,

        'data' => [
            'alarmas' => $eventosTabla,

            'resumen' => $resumen,

            'tendencia' => $tendencia,

            'top' => $top,

            'intermitencias' => [
                'cantidad' => count(
                    $intermitenciasTabla
                ),

                'dias_consultados' => 2,

                'criterio' => (
                    'mas_de_2_caidas_en_un_mismo_dia'
                ),
            ],
        ],
    ]);

} catch (Throwable $exception) {
    error_log(
        $exception->getMessage()
    );

    jsonResponse([
        'ok' => false,
        'error' => (
            $exception->getMessage()
        ),
    ], 503);
}