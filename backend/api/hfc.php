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

            $puntosSobre80 = is_numeric($port['puntos_sobre_80'] ?? null)
                ? (int) $port['puntos_sobre_80']
                : 0;
            $muestrasAnalizadas = is_numeric($port['muestras_analizadas'] ?? null)
                ? (int) $port['muestras_analizadas']
                : 0;

            $detalle = $puntosSobre80 > 0
                ? sprintf(
                    '%d puntos por encima del 80%%; porcentaje mostrado = promedio de esos puntos',
                    $puntosSobre80
                )
                : 'Degradación de señal confirmada por SNR';

            $rows[] = [
                'equipo' => $group['cmts'],
                'puerto' => $port['puerto'],
                'valor' => (float) $port['valor'],
                'unidad' => '%',
                'estado' => (string) ($port['estado'] ?? ''),
                'tipo' => (string) ($port['tipo'] ?? ''),
                'detalle' => $detalle,
                'bw' => $port['bw'] ?? null,
                'ruido' => $port['ruido'] ?? null,
                'puntos_sobre_80' => $puntosSobre80,
                'muestras_analizadas' => $muestrasAnalizadas,
            ];
        }
    }

    $sources['saturacion_cmts']['ok'] = true;
} catch (Throwable $error) {
    error_log('HFC saturacion_cmts: ' . $error->getMessage());
}

usort(
    $rows,
    static function (array $a, array $b): int {
        $porPuntos = $b['puntos_sobre_80'] <=> $a['puntos_sobre_80'];
        if ($porPuntos !== 0) {
            return $porPuntos;
        }

        return $b['valor'] <=> $a['valor'];
    }
);

$ok = $sources['saturacion_cmts']['ok'];
jsonResponse(
    [
        'ok' => $ok,
        'data' => ['estado_actual_hfc' => $rows],
        'sources' => $sources,
    ],
    $ok ? 200 : 503
);
