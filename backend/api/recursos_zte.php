<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/bootstrap.php';

requireMethod('GET');

try {
    $response = datosClient()->get('/api/olt/recursos-zte/licencias-bajas');
    $body = $response['body'];

    if (
        $response['status'] < 200
        || $response['status'] >= 300
        || ($body['ok'] ?? false) !== true
        || !is_numeric($body['data']['umbral_pct'] ?? null)
        || !is_array($body['data']['licencias'] ?? null)
    ) {
        throw new RuntimeException('Respuesta inválida de recursos ZTE');
    }

    $licencias = [];
    foreach ($body['data']['licencias'] as $fila) {
        if (
            !is_array($fila)
            || !is_string($fila['olt'] ?? null)
            || !is_string($fila['recurso'] ?? null)
            || !is_numeric($fila['usado'] ?? null)
            || !is_numeric($fila['disponible'] ?? null)
            || !is_numeric($fila['total'] ?? null)
            || !is_numeric($fila['porcentaje_disponible'] ?? null)
            || !is_string($fila['actualizado_en'] ?? null)
        ) {
            throw new RuntimeException('Lectura inválida de recursos ZTE');
        }

        $porcentaje = (float) $fila['porcentaje_disponible'];
        if (!is_finite($porcentaje) || $porcentaje < 0.0 || $porcentaje >= 15.0) {
            throw new RuntimeException('Porcentaje inválido de recursos ZTE');
        }

        $licencias[] = [
            'olt' => $fila['olt'],
            'recurso' => $fila['recurso'],
            'usado' => $fila['usado'],
            'disponible' => $fila['disponible'],
            'total' => $fila['total'],
            'porcentaje_disponible' => $porcentaje,
            'actualizado_en' => $fila['actualizado_en'],
        ];
    }

    jsonResponse([
        'ok' => true,
        'data' => [
            'umbral_pct' => (float) $body['data']['umbral_pct'],
            'licencias' => $licencias,
        ],
    ]);
} catch (Throwable $error) {
    error_log('Recursos ZTE: ' . $error->getMessage());
    jsonResponse([
        'ok' => false,
        'error' => 'Servicio de recursos ZTE no disponible',
    ], 503);
}
