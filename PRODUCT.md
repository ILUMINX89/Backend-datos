# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- Operadores del NOC que supervisan continuamente la red y necesitan detectar excepciones con rapidez.
- Personal de soporte e ingeniería de red que investiga equipos, alarmas y condiciones anormales.
- Supervisores que necesitan entender el estado operativo y la prioridad de los incidentes.

Los usuarios trabajan principalmente en pantallas de escritorio o monitores del NOC durante jornadas prolongadas. Deben identificar elementos afectados, distinguir criticidad y decidir cuándo investigar, escalar o intervenir.

## Product Purpose

NOC BOA permite supervisar la infraestructura FTTH/HFC y OLT con datos operativos reales. Su objetivo es reducir el tiempo necesario para encontrar problemas entre grandes volúmenes de datos y dirigir la atención hacia los elementos que requieren acción inmediata.

El producto tiene éxito cuando los operadores pueden detectar caídas, alarmas y condiciones anormales, priorizarlas por severidad y actuar sin tener que revisar manualmente todos los equipos.

## Positioning

NOC BOA es una herramienta operacional de Network Operations Center, no un dashboard genérico de inteligencia de negocio. Combina información accionable y de alta densidad sobre infraestructura FTTH/HFC con una lectura rápida de estados, severidades y excepciones alimentadas por el backend, InfluxDB y MySQL.

## Operating Context

- Supervisión continua desde estaciones de escritorio y monitores del NOC.
- Identificación de equipos o elementos de red con problemas.
- Detección y revisión de alarmas, caídas, temperaturas y otros indicadores de OLT.
- Priorización de eventos críticos frente a advertencias.
- Investigación, escalamiento o intervención según la severidad y el elemento afectado.
- Búsqueda de excepciones antes que revisión exhaustiva de equipos en estado normal.

## Capabilities and Constraints

- Los datos operativos provienen del backend existente y de sus integraciones con InfluxDB y MySQL.
- Deben preservarse los contratos de API y los endpoints existentes salvo que una necesidad explícita requiera cambiarlos.
- La lógica del backend, las consultas y la estructura de datos no se modifican por razones exclusivamente visuales.
- La interfaz debe mantener funcionando las integraciones actuales.
- La interfaz debe ser responsive, aprovechar eficientemente el espacio y evitar desbordamiento horizontal innecesario.
- Las vistas de excepciones de temperatura deben priorizar los equipos que superan los umbrales configurados y evitar llenar la pantalla con equipos normales.
- Severidades confirmadas para temperatura OLT:
  - 70 °C o superior: advertencia, asociada actualmente con amarillo.
  - 80 °C o superior: severidad alta, asociada actualmente con naranja.
  - 90 °C o superior: estado crítico, asociado actualmente con rojo.
- Debe conservarse la nomenclatura técnica existente, incluidos NOC, OLT, FTTH, HFC, alarmas, caídas, temperatura y estado.

## Brand Commitments

- Nombre del producto: NOC BOA.
- Debe conservarse la identidad visual y cualquier activo de marca existente en el proyecto.
- La experiencia debe sentirse como una herramienta profesional de Network Operations Center: operacional, sobria y orientada a decisiones.
- Debe priorizar información accionable, claridad y densidad útil sobre decoración, patrones de landing page o tarjetas genéricas de BI.

## Evidence on Hand

- Interfaz PHP funcional en `frontend/`, con navegación, vistas de alarmas, reportes, configuración y estado de red.
- API FastAPI en `microservicios/`, con dominios de alarmas, caídas, correlación, CRC, saturación y temperatura OLT.
- Integraciones existentes con InfluxDB y MySQL.
- Pruebas automatizadas para microservicios OLT en `tests/`.
- No se han confirmado testimonios, estudios de caso, métricas comerciales ni afirmaciones externas; el trabajo futuro no debe inventarlos.

## Product Principles

1. Hacer visibles primero las excepciones que requieren una decisión o acción.
2. Mantener alta densidad de información sin sacrificar jerarquía, legibilidad ni velocidad de lectura.
3. Preservar la verdad operacional de los datos y la estabilidad de las integraciones existentes.
4. Diseñar para supervisión prolongada, con señales claras y distracciones mínimas.
5. Mejorar de forma progresiva, revisable y reversible, conservando el comportamiento actual.

## Accessibility & Inclusion

- Priorizar conformidad WCAG AA cuando sea razonable.
- Mantener contraste y tamaños de texto adecuados para supervisión prolongada.
- No depender exclusivamente del color para comunicar estados o criticidad; acompañarlo con texto, iconos o indicadores equivalentes.
- Evitar animaciones innecesarias y elementos visuales que distraigan al operador.
