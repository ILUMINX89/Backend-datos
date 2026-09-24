<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/bootstrap.php';

requireMethod('POST');

try {
    $response = datosClient()->post('/api/cmts/saturacion/actualizar');
    jsonResponse($response['body'], $response['status']);
} catch (Throwable $error) {
    error_log('HFC actualizar: ' . $error->getMessage());
    jsonResponse(['ok' => false, 'error' => 'No se pudo iniciar la actualización HFC'], 503);
}
