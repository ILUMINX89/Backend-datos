<?php
declare(strict_types=1);

require_once __DIR__ . '/../lib/bootstrap.php';

requireMethod('GET');

try {
    $response = datosClient()->get('/api/olt/intermitencias', ['dias' => 2]);
    $body = $response['body'];

    if (
        $response['status'] < 200
        || $response['status'] >= 300
        || ($body['ok'] ?? false) !== true
        || !is_array($body['data']['datos'] ?? null)
    ) {
        throw new RuntimeException('Respuesta invalida de intermitencias FTTH');
    }

    $rows = [];
    foreach ($body['data']['datos'] as $olt) {
        if (!is_array($olt) || !is_array($olt['puertos'] ?? null)) {
            throw new RuntimeException('Estructura invalida de OLT en intermitencias FTTH');
        }
        foreach ($olt['puertos'] as $puerto) {
            if (!is_array($puerto) || !is_array($puerto['dias'] ?? null)) {
                throw new RuntimeException('Estructura invalida de puerto en intermitencias FTTH');
            }
            foreach ($puerto['dias'] as $dia) {
                if (!is_array($dia)) {
                    throw new RuntimeException('Estructura invalida de dia en intermitencias FTTH');
                }
                $rows[] = [
                    'olt' => $olt['olt'] ?? null,
                    'puerto' => $puerto['puerto'] ?? null,
                    'dia' => $dia['dia'] ?? null,
                    'cantidad_caidas' => $dia['cantidad_caidas'] ?? null,
                    'tiempo_total_caido_minutos' => $dia['tiempo_total_caido_minutos'] ?? null,
                ];
            }
        }
    }

    jsonResponse(['ok' => true, 'data' => ['intermitencias' => $rows]]);
} catch (Throwable $error) {
    error_log('Intermitencias FTTH: ' . $error->getMessage());
    jsonResponse(['ok' => false, 'data' => ['intermitencias' => []]], 503);
}
