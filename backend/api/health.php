<?php
declare(strict_types=1);
require_once __DIR__ . '/../lib/bootstrap.php';
requireMethod('GET');
try {
    $response = datosClient()->get('/health');
    jsonResponse($response['body'], $response['status']);
} catch (Throwable $error) {
    error_log('Health Backend Datos: ' . $error->getMessage());
    jsonResponse(['ok' => false, 'error' => 'Servicio de datos no disponible'], 503);
}
