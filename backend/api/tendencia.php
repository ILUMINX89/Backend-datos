<?php
declare(strict_types=1);
require_once __DIR__ . '/../lib/bootstrap.php';
requireMethod('GET');
$horas = optionalInt('horas', 1, 168) ?? 24;
forward(static fn (MicroserviceClient $client) => $client->get('/alarmas/tendencia', ['horas' => $horas]));
