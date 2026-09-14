<?php
declare(strict_types=1);

final class MicroserviceClient
{
    public function __construct(
        private readonly string $baseUrl,
        private readonly int $timeout = 8,
        private readonly int $connectTimeout = 3,
    ) {
        if (!extension_loaded('curl')) {
            throw new RuntimeException('La extension cURL de PHP no esta disponible');
        }
    }

    public function get(string $path, array $query = []): array
    {
        $url = $this->buildUrl($path, $query);
        return $this->request('GET', $url);
    }

    public function post(string $path, array $body = []): array
    {
        return $this->request('POST', $this->buildUrl($path), $body);
    }

    private function buildUrl(string $path, array $query = []): string
    {
        $url = rtrim($this->baseUrl, '/') . '/' . ltrim($path, '/');
        $query = array_filter($query, static fn ($value) => $value !== null && $value !== '');
        return $query ? $url . '?' . http_build_query($query, '', '&', PHP_QUERY_RFC3986) : $url;
    }

    private function request(string $method, string $url, ?array $body = null): array
    {
        $handle = curl_init($url);
        if ($handle === false) {
            throw new RuntimeException('No fue posible inicializar el cliente HTTP');
        }

        $headers = ['Accept: application/json'];
        $options = [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => $this->timeout,
            CURLOPT_CONNECTTIMEOUT => $this->connectTimeout,
            CURLOPT_CUSTOMREQUEST => $method,
            CURLOPT_HTTPHEADER => $headers,
        ];

        if ($body !== null) {
            $encoded = json_encode($body, JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR);
            $options[CURLOPT_POSTFIELDS] = $encoded;
            $options[CURLOPT_HTTPHEADER][] = 'Content-Type: application/json';
        }

        curl_setopt_array($handle, $options);
        $raw = curl_exec($handle);
        if ($raw === false) {
            $message = curl_error($handle);
            curl_close($handle);
            throw new RuntimeException('Servicio de alarmas no disponible: ' . $message);
        }

        $status = (int) curl_getinfo($handle, CURLINFO_RESPONSE_CODE);
        curl_close($handle);
        try {
            $decoded = json_decode($raw, true, 512, JSON_THROW_ON_ERROR);
        } catch (JsonException $exception) {
            throw new RuntimeException('El servicio devolvio una respuesta JSON invalida', 0, $exception);
        }

        if (!is_array($decoded)) {
            throw new RuntimeException('El servicio devolvio una respuesta inesperada');
        }

        return ['status' => $status, 'body' => $decoded];
    }
}
