<?php
declare(strict_types=1);
require_once __DIR__ . '/../lib/bootstrap.php';
requireMethod('GET');
$limit = optionalInt('limit', 1, 100) ?? 5;
forward(static fn (MicroserviceClient $client) => $client->get('/alarmas/top', ['limit' => $limit]));
