<?php
declare(strict_types=1);
require_once __DIR__ . '/../lib/bootstrap.php';
requireMethod('GET');
forward(static fn (MicroserviceClient $client) => $client->get('/health'));
