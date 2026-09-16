<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/bootstrap.php';

requireMethod('GET');

try {
    $response = datosClient()->get(
        '/api/olt/perdida-latencia/actual'
    );
    $body = $response['body'];

    if (
        $response['status'] < 200
        || $response['status'] >= 300
        || ($body['ok'] ?? false) !== true
        || !is_array($body['data']['datos'] ?? null)
    ) {
        throw new RuntimeException(
            'Respuesta inválida de pérdida y latencia'
        );
    }

    $rows = [];

    foreach ($body['data']['datos'] as $row) {
        if (
            !is_string($row['equipo'] ?? null)
            || !is_numeric($row['valor'] ?? null)
            || !in_array($row['estado'] ?? null, ['Pérdida', 'Latencia'], true)
        ) {
            throw new RuntimeException('Lectura inválida de pérdida y latencia');
        }

        $valor = (float) $row['valor'];
        $estado = $row['estado'];
        if (($estado === 'Pérdida' && $valor <= 10.0)
            || ($estado === 'Latencia' && $valor <= 50.0)) {
            continue;
        }

        $rows[] = [
            'equipo' => $row['equipo'],
            'valor' => $valor,
            'unidad' => $estado === 'Pérdida' ? '%' : 'ms',
            'estado' => $estado,
            'nivel' => $estado === 'Pérdida' && $valor === 100.0
                ? 'rojo'
                : ($row['nivel'] ?? 'neutral'),
        ];
    }

    jsonResponse([
        'ok' => true,
        'data' => [
            'datos' => $rows,
        ],
    ]);
} catch (Throwable $error) {
    error_log('Pérdida y latencia OLT: ' . $error->getMessage());
    jsonResponse(
        [
            'ok' => false,
            'error' => 'Servicio de pérdida y latencia no disponible',
        ],
        503
    );
}
