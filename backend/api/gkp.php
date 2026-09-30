<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/bootstrap.php';

requireMethod('GET');

$definitions = [
    'caidas' => [
        '/api/olt/caidas/actuales',
        'Caída actual',
        'min',
    ],
    'saturacion' => [
        '/api/olt/saturacion/actual',
        'Saturación uplink',
        '%',
    ],
    'crc' => [
        '/api/olt/crc/actual',
        'Error CRC',
        'CRC/s',
    ],
];

$rows = [];
$sources = [];
$gkpStartedAt = microtime(true);

foreach ($definitions as $source => [$path, $state, $unit]) {
    $sourceStartedAt = microtime(true);

    try {
        $response = datosClient()->get($path);
        $body = $response['body'];

        if (
            $response['status'] < 200
            || $response['status'] >= 300
            || ($body['ok'] ?? false) !== true
            || !is_array($body['data']['datos'] ?? null)
        ) {
            throw new RuntimeException(
                'Respuesta inválida de ' . $source
            );
        }

        $sourceRows = [];

        foreach ($body['data']['datos'] as $group) {
            if (
                !is_string($group['olt'] ?? null)
                || !is_array($group['puertos'] ?? null)
            ) {
                throw new RuntimeException(
                    'Grupo inválido de ' . $source
                );
            }

            foreach ($group['puertos'] as $port) {
                if (!is_string($port['puerto'] ?? null)) {
                    throw new RuntimeException(
                        'Puerto inválido de ' . $source
                    );
                }

                /*
                 * CAÍDAS
                 *
                 * Sólo interesa CAIDO_ACTUAL:
                 *
                 * - el puerto está reportando
                 * - las últimas muestras están en tráfico 0
                 *
                 * No mostrar:
                 *
                 * - SIN_MUESTRAS_RECIENTES
                 * - CAIDO_SIN_FECHA
                 *
                 * Estos casos representan equipos/puertos
                 * que dejaron de reportar o de los cuales
                 * no tenemos información reciente suficiente.
                 */
                if ($source === 'caidas') {
                    $estadoOrigen = (string) (
                        $port['estado'] ?? ''
                    );

                    if ($estadoOrigen !== 'CAIDO_ACTUAL') {
                        continue;
                    }

                    $value = (
                        $port['tiempo_sin_trafico_minutos']
                        ?? null
                    );

                    /*
                     * Una caída actual válida debe tener
                     * duración calculable.
                     */
                    if (
                        $value === null
                        || !is_numeric($value)
                        || (float) $value <= 0
                    ) {
                        continue;
                    }

                    $detail = 'Estado de origen: CAIDO_ACTUAL';
                    $fechaEvento = $port['ultima_muestra'] ?? null;
                } else {
                    /*
                     * SATURACIÓN / CRC
                     *
                     * Los endpoints /actual ya entregan
                     * solamente la condición vigente.
                     */
                    $value = $port['valor'] ?? null;

                    if (!is_numeric($value)) {
                        throw new RuntimeException(
                            'Valor inválido de ' . $source
                        );
                    }

                    /*
                     * No mostrar valores en cero.
                     */
                    if ((float) $value <= 0) {
                        continue;
                    }

                    $detail = (
                        'Última muestra en ventana de 15 minutos'
                    );
                    $fechaEvento = $port['fecha'] ?? null;
                }

                $timestamp = is_string($fechaEvento)
                    ? strtotime($fechaEvento)
                    : false;

                $sourceRows[] = [
                    'equipo' => $group['olt'],
                    'puerto' => $port['puerto'],
                    'valor' => (float) $value,
                    'unidad' => $unit,
                    'estado' => $state,
                    'detalle' => $detail,
                    'fecha_evento' => $fechaEvento,
                    'fecha_evento_ts' => $timestamp !== false ? $timestamp : 0,
                ];
            }
        }

        array_push($rows, ...$sourceRows);

        $sources[$source] = [
            'ok' => true,
            'duration_ms' => round(
                (microtime(true) - $sourceStartedAt) * 1000,
                1
            ),
        ];
    } catch (Throwable $error) {
        error_log(
            'GKP ' . $source . ': ' . $error->getMessage()
        );

        $sources[$source] = [
            'ok' => false,
            'duration_ms' => round(
                (microtime(true) - $sourceStartedAt) * 1000,
                1
            ),
        ];
    }

    error_log(
        sprintf(
            'GKP source=%s duration=%.3fs ok=%s',
            $source,
            microtime(true) - $sourceStartedAt,
            $sources[$source]['ok'] ? 'true' : 'false'
        )
    );
}

usort(
    $rows,
    static fn ($a, $b) =>
        ($b['fecha_evento_ts']
            <=> $a['fecha_evento_ts'])
        ?: strnatcasecmp(
            $a['equipo'],
            $b['equipo']
        )
        ?: strnatcasecmp(
            $a['puerto'],
            $b['puerto']
        )
);

foreach ($rows as &$row) {
    unset($row['fecha_evento_ts']);
}
unset($row);

$ok = in_array(
    true,
    array_column($sources, 'ok'),
    true
);

error_log(
    sprintf(
        'GKP total duration=%.3fs',
        microtime(true) - $gkpStartedAt
    )
);

jsonResponse(
    [
        'ok' => $ok,
        'data' => [
            'estado_actual_red' => $rows,
        ],
        'sources' => $sources,
    ],
    $ok ? 200 : 503
);
