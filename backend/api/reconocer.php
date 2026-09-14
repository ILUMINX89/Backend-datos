<?php
declare(strict_types=1);
require_once __DIR__ . '/../lib/bootstrap.php';
requireMethod('POST');
$body = readJsonBody();
$id = trim((string) ($body['id'] ?? ''));
$usuario = trim((string) ($body['usuario'] ?? ''));
if ($id === '' || strlen($id) > 200 || $usuario === '' || strlen($usuario) > 100) {
    jsonResponse(['ok' => false, 'error' => 'id y usuario son obligatorios'], 400);
}
forward(static fn (MicroserviceClient $client) => $client->post(
    '/alarmas/' . rawurlencode($id) . '/reconocer',
    ['usuario' => $usuario],
));
