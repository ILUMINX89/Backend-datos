<?php
declare(strict_types=1);
require_once __DIR__ . '/../lib/bootstrap.php';
requireMethod('GET');
$id = trim((string) ($_GET['id'] ?? ''));
if ($id === '' || strlen($id) > 200) {
    jsonResponse(['ok' => false, 'error' => 'Parametro id invalido'], 400);
}
forward(static fn (MicroserviceClient $client) => $client->get('/alarmas/' . rawurlencode($id)));
