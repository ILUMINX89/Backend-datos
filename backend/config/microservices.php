<?php
declare(strict_types=1);

return [
    'alarmas' => [
        'base_url' => getenv('ALARMAS_SERVICE_URL') ?: 'http://127.0.0.1:8001',
        'timeout' => 8,
        'connect_timeout' => 3,
    ],
];
