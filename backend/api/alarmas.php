<?php
declare(strict_types=1);
require_once __DIR__ . '/../lib/bootstrap.php';
requireMethod('GET');

$tipo = optionalInt('tipo', 1, 3);
$limit = optionalInt('limit', 1, 1000) ?? 100;
$estado = isset($_GET['estado']) ? substr(trim((string) $_GET['estado']), 0, 30) : null;
$q = isset($_GET['q']) ? substr(trim((string) $_GET['q']), 0, 200) : null;
forward(static fn (MicroserviceClient $client) => $client->get('/alarmas', compact('tipo', 'estado', 'q', 'limit')));
