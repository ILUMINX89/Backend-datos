<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/bootstrap.php';

requireMethod('GET');

$rows = [];
$sources = ['intermitencias' => ['ok' => false]];

try {
    $response = datosClient()->get('/api/cmts/intermitencias/actual');
    $body = $response['body'];

    if (
        $response['status'] < 200
        || $response['status'] >= 300
        || ($body['ok'] ?? false) !== true
        || !is_array($body['data']['datos'] ?? null)
    ) {
        throw new RuntimeException('Respuesta invalida de intermitencias HFC');
    }

    $rows = array_values($body['data']['datos']);
    $sources['intermitencias']['ok'] = true;
} catch (Throwable $error) {
    error_log('Intermitencias HFC: ' . $error->getMessage());
}

$ok = $sources['intermitencias']['ok'];
jsonResponse(
    [
        'ok' => $ok,
        'data' => ['intermitencias' => $rows],
        'sources' => $sources,
    ],
    $ok ? 200 : 503
);
