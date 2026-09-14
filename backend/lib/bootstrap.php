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

function alarmasClient(): MicroserviceClient
{
    $services = require __DIR__ . '/../config/microservices.php';
    $config = $services['alarmas'];
    return new MicroserviceClient(
        $config['base_url'],
        (int) $config['timeout'],
        (int) $config['connect_timeout'],
    );
}

function forward(callable $operation): never
{
    try {
        $response = $operation(alarmasClient());
        jsonResponse($response['body'], $response['status']);
    } catch (Throwable $exception) {
        error_log($exception->getMessage());
        jsonResponse(['ok' => false, 'error' => 'Servicio de alarmas no disponible'], 503);
    }
}

function readJsonBody(): array
{
    $raw = file_get_contents('php://input');
    try {
        $body = json_decode($raw ?: '{}', true, 512, JSON_THROW_ON_ERROR);
    } catch (JsonException) {
        jsonResponse(['ok' => false, 'error' => 'JSON invalido'], 400);
    }
    return is_array($body) ? $body : [];
}

function optionalInt(string $name, int $min, int $max): ?int
{
    if (!isset($_GET[$name]) || $_GET[$name] === '') {
        return null;
    }
    $value = filter_var($_GET[$name], FILTER_VALIDATE_INT);
    if ($value === false || $value < $min || $value > $max) {
        jsonResponse(['ok' => false, 'error' => "Parametro {$name} invalido"], 400);
    }
    return $value;
}
