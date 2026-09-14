<?php
declare(strict_types=1);
require_once __DIR__ . '/../lib/bootstrap.php';
requireMethod('GET');

try {
    $client = alarmasClient();
    $requests = [
        'alarmas' => $client->get('/alarmas', ['limit' => 100]),
        'resumen' => $client->get('/alarmas/resumen'),
        'tendencia' => $client->get('/alarmas/tendencia', ['horas' => 24]),
        'top' => $client->get('/alarmas/top', ['limit' => 5]),
    ];
    $data = [];
    foreach ($requests as $name => $response) {
        if ($response['status'] < 200 || $response['status'] >= 300 || !($response['body']['ok'] ?? false)) {
            throw new RuntimeException("Fallo la consulta {$name}");
        }
        $data[$name] = $response['body']['data'] ?? null;
    }
    jsonResponse(['ok' => true, 'data' => $data]);
} catch (Throwable $exception) {
    error_log($exception->getMessage());
    jsonResponse(['ok' => false, 'error' => 'Datos temporalmente no disponibles'], 503);
}
