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

    jsonResponse([
        'ok' => true,
        'data' => [
            'datos' => $body['data']['datos'],
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
