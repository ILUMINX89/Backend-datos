<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/bootstrap.php';

requireMethod('GET');

$rows = [];
$sources = ['puertos_duplicados' => ['ok' => false]];

try {
    $response = datosClient()->get('/api/cmts/puertos-duplicados/actual');
    $body = $response['body'];

    if (
        $response['status'] < 200
        || $response['status'] >= 300
        || ($body['ok'] ?? false) !== true
        || !is_array($body['data']['datos'] ?? null)
    ) {
        throw new RuntimeException('Respuesta invalida de puertos duplicados HFC');
    }

    $rows = array_values($body['data']['datos']);
    $sources['puertos_duplicados']['ok'] = true;
} catch (Throwable $error) {
    error_log('Puertos duplicados HFC: ' . $error->getMessage());
}

$ok = $sources['puertos_duplicados']['ok'];
jsonResponse(
    [
        'ok' => $ok,
        'data' => ['puertos_duplicados' => $rows],
        'sources' => $sources,
    ],
    $ok ? 200 : 503
);
