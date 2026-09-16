<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/bootstrap.php';

requireMethod('GET');

try {
    $response = datosClient()->get(
        '/api/olt/temperatura/actual'
    );

    $body = $response['body'];

    if (
        $response['status'] < 200
        || $response['status'] >= 300
        || ($body['ok'] ?? false) !== true
        || !is_array(
            $body['data']['datos'] ?? null
        )
    ) {
        throw new RuntimeException(
            'Respuesta inválida de temperatura'
        );
    }

    $rows = [];

    foreach (
        $body['data']['datos'] as $row
    ) {
        if (
            !is_string(
                $row['olt'] ?? null
            )
            || !is_numeric(
                $row['temperatura'] ?? null
            )
            || !is_finite(
                (float) $row['temperatura']
            )
        ) {
            throw new RuntimeException(
                'Lectura inválida de temperatura'
            );
        }

        $temperatura = (float) (
            $row['temperatura']
        );

        /*
         * Protección adicional.
         * No mostrar valores menores a 70 °C.
         */
        if ($temperatura < 70.0) {
            continue;
        }

        $rows[] = [
            'equipo' => $row['olt'],
            'temperatura' => $temperatura,
            'estado' => $row['estado'] ?? 'Advertencia',
            'nivel' => $row['nivel'] ?? 'amarillo',
        ];
    }

    jsonResponse(
        [
            'ok' => true,
            'data' => [
                'temperaturas' => $rows,
            ],
        ]
    );
} catch (Throwable $error) {
    error_log(
        'Temperatura OLT: '
        . $error->getMessage()
    );

    jsonResponse(
        [
            'ok' => false,
            'error' => (
                'Servicio de temperatura '
                . 'no disponible'
            ),
        ],
        503
    );
}
