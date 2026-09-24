<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/bootstrap.php';

requireMethod('GET');

try {
    $response = datosClient()->get('/api/cmts/saturacion/estado');
    jsonResponse($response['body'], $response['status']);
} catch (Throwable $error) {
    error_log('HFC estado: ' . $error->getMessage());
    jsonResponse(['ok' => false, 'error' => 'No se pudo consultar el estado HFC'], 503);
}
