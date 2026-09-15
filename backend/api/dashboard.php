<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/bootstrap.php';

requireMethod('GET');

try {
    $client = alarmasClient();

    // Una sola llamada al microservicio.
    $response = $client->get('/alarmas', [
        'limit' => 1000,
    ]);

    if (
        $response['status'] < 200 ||
        $response['status'] >= 300 ||
        !($response['body']['ok'] ?? false)
    ) {
        throw new RuntimeException('Fallo la consulta de alarmas');
    }

    $alarmas = $response['body']['data'] ?? [];

    // ==========================================
    // Resumen
    // ==========================================

    $resumen = [
        'total' => 0,
        'tipo1' => 0,
        'tipo2' => 0,
        'tipo3' => 0,
    ];

    foreach ($alarmas as $alarma) {
        if (($alarma['estado'] ?? '') !== 'ACTIVA') {
            continue;
        }

        $resumen['total']++;

        $tipo = (int) ($alarma['tipo'] ?? 0);

        if ($tipo === 1) {
            $resumen['tipo1']++;
        } elseif ($tipo === 2) {
            $resumen['tipo2']++;
        } elseif ($tipo === 3) {
            $resumen['tipo3']++;
        }
    }

    // ==========================================
    // Top por OLT
    // ==========================================

    $conteoOlts = [];

    foreach ($alarmas as $alarma) {
        $olt = (string) ($alarma['olt'] ?? '');

        if ($olt === '') {
            continue;
        }

        if (!isset($conteoOlts[$olt])) {
            $conteoOlts[$olt] = 0;
        }

        $conteoOlts[$olt]++;
    }

    arsort($conteoOlts);

    $top = [];

    foreach (array_slice($conteoOlts, 0, 5, true) as $equipo => $total) {
        $top[] = [
            'equipo' => $equipo,
            'total' => $total,
        ];
    }

    // Tendencia todavía no implementada.
    $tendencia = [];

    jsonResponse([
        'ok' => true,
        'data' => [
            'alarmas' => $alarmas,
            'resumen' => $resumen,
            'tendencia' => $tendencia,
            'top' => $top,
        ],
    ]);

} catch (Throwable $exception) {
    error_log($exception->getMessage());

    jsonResponse([
        'ok' => false,
        'error' => $exception->getMessage(),
    ], 503);
}