<?php

declare(strict_types=1);

require_once __DIR__ . '/../lib/bootstrap.php';

requireMethod('GET');

$cachePath = __DIR__ . '/../storage/hfc_estado.json';
$refreshRequested = ($_GET['refresh'] ?? '') === '1';

function readHfcCache(string $path): ?array
{
    if (!is_file($path)) {
        return null;
    }
    try {
        $cache = json_decode((string) file_get_contents($path), true, 512, JSON_THROW_ON_ERROR);
    } catch (Throwable $error) {
        error_log('HFC cache: ' . $error->getMessage());
        return null;
    }
    return is_array($cache)
        && is_string($cache['actualizado_en'] ?? null)
        && is_array($cache['estado_actual_hfc'] ?? null)
        ? $cache
        : null;
}

function writeHfcCache(string $path, array $cache): void
{
    $directory = dirname($path);
    if (!is_dir($directory) && !mkdir($directory, 0775, true) && !is_dir($directory)) {
        throw new RuntimeException('No fue posible crear el directorio de cache HFC');
    }
    $temporary = tempnam($directory, '.hfc_estado.json.');
    if ($temporary === false) {
        throw new RuntimeException('No fue posible crear el cache temporal HFC');
    }
    try {
        $json = json_encode($cache, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT | JSON_THROW_ON_ERROR);
        if (file_put_contents($temporary, $json . PHP_EOL, LOCK_EX) === false) {
            throw new RuntimeException('No fue posible escribir el cache temporal HFC');
        }
        if (!rename($temporary, $path)) {
            throw new RuntimeException('No fue posible reemplazar el cache HFC');
        }
    } finally {
        if (is_file($temporary)) {
            unlink($temporary);
        }
    }
}

function fetchHfcRows(): array
{
    $services = require __DIR__ . '/../config/microservices.php';
    $config = $services['hfc'];
    $client = new MicroserviceClient($config['base_url'], 0, (int) $config['connect_timeout']);
    $response = $client->get('/api/cmts/saturacion/actual', ['refresh' => 1]);
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
            $samples = is_numeric($port['muestras_analizadas'] ?? null) ? (int) $port['muestras_analizadas'] : 0;
            $rows[] = [
                'equipo' => $group['cmts'], 'puerto' => $port['puerto'],
                'valor' => (float) $port['valor'], 'unidad' => '%',
                'estado' => (string) ($port['estado'] ?? ''), 'tipo' => (string) ($port['tipo'] ?? ''),
                'detalle' => $points > 0
                    ? sprintf('%d puntos por encima del 90%%; porcentaje mostrado = promedio de esos puntos', $points)
                    : 'Degradación de señal confirmada por SNR',
                'bw' => $port['bw'] ?? null, 'ruido' => $port['ruido'] ?? null,
                'puntos_sobre_90' => $points, 'muestras_analizadas' => $samples,
            ];
        }
    }
    usort($rows, static function (array $a, array $b): int {
        return ($b['puntos_sobre_90'] <=> $a['puntos_sobre_90']) ?: ($b['valor'] <=> $a['valor']);
    });
    return $rows;
}

$cache = readHfcCache($cachePath);
if (!$refreshRequested && $cache !== null) {
    jsonResponse(['ok' => true, 'actualizado_en' => $cache['actualizado_en'], 'data' => $cache]);
}

set_time_limit(0);
ignore_user_abort(true);
try {
    $rows = fetchHfcRows();
    $cache = ['actualizado_en' => date(DATE_ATOM), 'estado_actual_hfc' => $rows];
    writeHfcCache($cachePath, $cache);
    jsonResponse(['ok' => true, 'actualizado_en' => $cache['actualizado_en'], 'data' => $cache]);
} catch (Throwable $error) {
    error_log('HFC saturacion_cmts: ' . $error->getMessage());
    $cache = readHfcCache($cachePath);
    if ($cache !== null) {
        jsonResponse([
            'ok' => true, 'actualizado_en' => $cache['actualizado_en'],
            'actualizacion_fallida' => true,
            'error' => 'La actualización falló; se muestran los últimos datos válidos.',
            'data' => $cache,
        ]);
    }
    jsonResponse(['ok' => false, 'error' => 'No se pudo obtener el estado HFC'], 503);
}
