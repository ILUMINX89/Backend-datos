<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/bootstrap.php';

requireMethod('GET');

$rows = [];
$sources = ['puertos_docsis' => ['ok' => false]];

try {
    $response = datosClient()->get('/api/cmts/puertos-docsis/actual');
    $body = $response['body'];

    if (
        $response['status'] < 200
        || $response['status'] >= 300
        || ($body['ok'] ?? false) !== true
        || !is_array($body['data']['datos'] ?? null)
    ) {
        throw new RuntimeException('Respuesta invalida de puertos DOCSIS');
    }

    $rows = array_values($body['data']['datos']);
    $sources['puertos_docsis']['ok'] = true;
} catch (Throwable $error) {
    error_log('Puertos DOCSIS: ' . $error->getMessage());
}

$ok = $sources['puertos_docsis']['ok'];
jsonResponse(
    [
        'ok' => $ok,
        'data' => ['puertos_docsis' => $rows],
        'sources' => $sources,
    ],
    $ok ? 200 : 503
);
