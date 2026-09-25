<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/bootstrap.php';

requireMethod('GET');

try {
    $response = datosClient()->get('/api/cmts/saturacion/actual');
    $body = $response['body'];
    if ($response['status'] < 200 || $response['status'] >= 300
        || ($body['ok'] ?? false) !== true || !is_array($body['data']['datos'] ?? null)) {
        throw new RuntimeException('Respuesta inválida de saturación CMTS');
    }

    $rows = [];
    foreach ($body['data']['datos'] as $group) {
        if (!is_string($group['cmts'] ?? null) || !is_array($group['puertos'] ?? null)) {
            throw new RuntimeException('Grupo CMTS inválido');
        }
        foreach ($group['puertos'] as $port) {
            if (!is_string($port['puerto'] ?? null) || !is_numeric($port['valor'] ?? null)) {
                throw new RuntimeException('Puerto CMTS inválido');
            }
            $points = is_numeric($port['puntos_sobre_90'] ?? null) ? (int) $port['puntos_sobre_90'] : 0;
            $rows[] = [
                'equipo' => $group['cmts'], 'puerto' => $port['puerto'],
                'valor' => (float) $port['valor'], 'unidad' => '%',
                'estado' => (string) ($port['estado'] ?? ''), 'tipo' => (string) ($port['tipo'] ?? ''),
                'detalle' => $points > 0
                    ? sprintf('%d puntos por encima del 90%%; porcentaje mostrado = promedio de esos puntos', $points)
                    : 'Degradación de señal confirmada por SNR',
                'bw' => $port['bw'] ?? null, 'ruido' => $port['ruido'] ?? null,
                'puntos_sobre_90' => $points,
                'muestras_analizadas' => is_numeric($port['muestras_analizadas'] ?? null)
                    ? (int) $port['muestras_analizadas'] : 0,
            ];
        }
    }
    usort($rows, static function (array $a, array $b): int {
        return ($b['puntos_sobre_90'] <=> $a['puntos_sobre_90']) ?: ($b['valor'] <=> $a['valor']);
    });
    jsonResponse([
        'ok' => true,
        'data' => [
            'estado_actual_hfc' => $rows,
            'actualizado_en' => $body['data']['generado_en'] ?? null,
        ],
    ]);
} catch (Throwable $error) {
    error_log('HFC saturacion_cmts: ' . $error->getMessage());
    jsonResponse(['ok' => false, 'error' => 'No se pudo consultar el estado HFC'], 503);
}
