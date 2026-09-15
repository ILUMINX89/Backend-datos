<?php
declare(strict_types=1);
require_once __DIR__ . '/../lib/bootstrap.php';
requireMethod('GET');

$definitions = [
    'caidas' => ['/api/olt/caidas/actuales', 'Caída actual', 'min'],
    'saturacion' => ['/api/olt/saturacion/actual', 'Saturación uplink', '%'],
    'crc' => ['/api/olt/crc/actual', 'Error CRC', 'CRC/s'],
];
$rows = [];
$sources = [];
foreach ($definitions as $source => [$path, $state, $unit]) {
    try {
        $response = datosClient()->get($path);
        $body = $response['body'];
        if ($response['status'] < 200 || $response['status'] >= 300 || ($body['ok'] ?? false) !== true
            || !is_array($body['data']['datos'] ?? null)) {
            throw new RuntimeException('Respuesta inválida de ' . $source);
        }
        $sourceRows = [];
        foreach ($body['data']['datos'] as $group) {
            if (!is_string($group['olt'] ?? null) || !is_array($group['puertos'] ?? null)) {
                throw new RuntimeException('Grupo inválido de ' . $source);
            }
            foreach ($group['puertos'] as $port) {
                if (!is_string($port['puerto'] ?? null)) {
                    throw new RuntimeException('Puerto inválido de ' . $source);
                }
                if ($source === 'caidas') {
                    $value = $port['tiempo_sin_trafico_minutos'] ?? null;
                    $detail = 'Estado de origen: ' . ($port['estado'] ?? 'N/D');
                } else {
                    $value = $port['valor'] ?? null;
                    if (!is_numeric($value)) {
                        throw new RuntimeException('Valor inválido de ' . $source);
                    }
                    $detail = 'Última muestra en ventana de 15 minutos';
                }
                if ($value !== null && !is_numeric($value)) {
                    throw new RuntimeException('Duración inválida');
                }
                $sourceRows[] = ['equipo' => $group['olt'], 'puerto' => $port['puerto'],
                    'valor' => $value === null ? null : (float) $value,
                    'unidad' => $unit, 'estado' => $state, 'detalle' => $detail];
            }
        }
        array_push($rows, ...$sourceRows);
        $sources[$source] = ['ok' => true];
    } catch (Throwable $error) {
        error_log('GKP ' . $source . ': ' . $error->getMessage());
        $sources[$source] = ['ok' => false];
    }
}
// State order is global; the frontend groups equipment without moving rows.
$priority = ['Caída actual' => 0, 'Saturación uplink' => 1, 'Error CRC' => 2];
usort($rows, static fn ($a, $b) => ($priority[$a['estado']] <=> $priority[$b['estado']])
    ?: strnatcasecmp($a['equipo'], $b['equipo']) ?: strnatcasecmp($a['puerto'], $b['puerto']));
$ok = in_array(true, array_column($sources, 'ok'), true);
jsonResponse(['ok' => $ok, 'data' => ['estado_actual_red' => $rows], 'sources' => $sources], $ok ? 200 : 503);
