<?php

declare(strict_types=1);

return [
    'datos' => [
        'base_url' => getenv('DATOS_SERVICE_URL') ?: 'http://127.0.0.1:8000',
        'timeout' => 180,
        'connect_timeout' => 3,
    ],
    'hfc' => [
        'base_url' => getenv('DATOS_SERVICE_URL') ?: 'http://127.0.0.1:8000',
        'timeout' => 0,
        'connect_timeout' => 3,
    ],
    'alarmas' => [
        'base_url' => getenv('ALARMAS_SERVICE_URL')
            ?: 'http://127.0.0.1:8001',

        'timeout' => 60,

        'connect_timeout' => 5,
    ],
];
