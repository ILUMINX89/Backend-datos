<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/bootstrap.php';

requireMethod('GET');

$rows = [];
$sources = ['saturacion_cmts' => ['ok' => false]];

try {
    $response = datosClient()->get('/api/cmts/saturacion/actual');
    $body = $response['body'];

    if (
        $response['status'] < 200
        || $response['status'] >= 300
        || ($body['ok'] ?? false) !== true
        || !is_array($body['data']['datos'] ?? null)
    ) {
        throw new RuntimeException('Respuesta inválida de saturación CMTS');
    }

    foreach ($body['data']['datos'] as $group) {
        if (!is_string($group['cmts'] ?? null) || !is_array($group['puertos'] ?? null)) {
            throw new RuntimeException('Grupo CMTS inválido');
        }
        foreach ($group['puertos'] as $port) {
            if (!is_string($port['puerto'] ?? null) || !is_numeric($port['valor'] ?? null)) {
                throw new RuntimeException('Puerto CMTS inválido');
            }
            $rows[] = [
                'equipo' => $group['cmts'],
                'puerto' => $port['puerto'],
                'valor' => (float) $port['valor'],
                'unidad' => '%',
                'estado' => 'Saturación CMTS',
                'detalle' => 'Última muestra disponible; utilización superior al 80%',
            ];
        }
    }
    $sources['saturacion_cmts']['ok'] = true;
} catch (Throwable $error) {
    error_log('HFC saturacion_cmts: ' . $error->getMessage());
}

$ok = $sources['saturacion_cmts']['ok'];
jsonResponse(
    [
        'ok' => $ok,
        'data' => ['estado_actual_hfc' => $rows],
        'sources' => $sources,
    ],
    $ok ? 200 : 503
);
