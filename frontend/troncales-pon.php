<?php
$pageTitle = 'Troncales PON';
$pageDescription = 'Consulta unificada de condiciones detectadas en las troncales PON.';
$pageSections = [
    ['id' => 'troncales-duplicadas', 'title' => 'Troncales duplicadas', 'description' => 'Resultados de detección de troncales duplicadas.'],
    ['id' => 'troncales-atenuadas', 'title' => 'Troncales atenuadas', 'description' => 'Resultados de detección de troncales atenuadas.'],
];
require __DIR__ . '/components/module-page.php';
