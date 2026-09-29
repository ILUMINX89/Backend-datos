<?php
declare(strict_types=1);

require_once __DIR__ . '/MicroserviceClient.php';

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

function jsonResponse(array $payload, int $status = 200): never
{
    http_response_code($status);
    echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function requireMethod(string $method): void
{
    if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== $method) {
        header('Allow: ' . $method);
        jsonResponse(['ok' => false, 'error' => 'Metodo no permitido'], 405);
    }
}

function datosClient(): MicroserviceClient
{
    $services = require __DIR__ . '/../config/microservices.php';
    $config = $services['datos'];
    return new MicroserviceClient($config['base_url'], (int) $config['timeout'], (int) $config['connect_timeout']);
}
