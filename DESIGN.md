---
name: NOC BOA
description: Sistema operacional de monitoreo FTTH/HFC orientado a detectar, entender, priorizar y actuar.
colors:
  canvas: "#020305"
  canvas-secondary: "#05070a"
  surface: "#080b10"
  surface-secondary: "#0b0f15"
  surface-hover: "#0e141d"
  border: "#192431"
  border-soft: "#101820"
  border-highlight: "#26384b"
  text-primary: "#f4f7fb"
  text-secondary: "#c2ccd6"
  text-muted: "#83919f"
  text-subtle: "#596775"
  primary: "#128cff"
  green: "#14cf7b"
  yellow: "#ffd229"
  orange: "#ff811a"
  red: "#ff3048"
  light-canvas: "#f2faff"
  light-surface: "#ffffff"
  light-text: "#06127a"
  light-secondary: "#526ac0"
  light-border: "#dceefb"
typography:
  headline:
    fontFamily: "Segoe UI, Inter, Arial, sans-serif"
    fontSize: "28px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Segoe UI, Inter, Arial, sans-serif"
    fontSize: "18px"
    fontWeight: 700
    lineHeight: 1.25
  body:
    fontFamily: "Segoe UI, Inter, Arial, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Segoe UI, Inter, Arial, sans-serif"
    fontSize: "11px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.055em"
rounded:
  xs: "4px"
  sm: "7px"
  md: "8px"
  lg: "12px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
components:
  button-secondary:
    backgroundColor: "{colors.surface-secondary}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.sm}"
    padding: "8px 12px"
  navigation-item:
    backgroundColor: "transparent"
    textColor: "{colors.text-muted}"
    rounded: "{rounded.md}"
    padding: "0 11px"
    height: "43px"
  navigation-item-active:
    backgroundColor: "#0d5aa1"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.md}"
    padding: "0 11px"
    height: "43px"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.lg}"
    padding: "16px"
  input:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.sm}"
    padding: "8px 10px"
  status-badge:
    backgroundColor: "{colors.red}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.xs}"
    padding: "4px 8px"
---

# Design System: NOC BOA

## Overview

**Creative North Star: "Torre de Control"**

NOC BOA es una consola técnica de vigilancia operacional: oscura por defecto, precisa y jerárquica. La interfaz debe permitir reconocer en segundos qué funciona, qué se desvía y qué exige atención. Su densidad es deliberadamente alta, pero cada nivel se separa mediante ritmo compacto, contraste controlado y capas tonales.

El sistema puede incorporar el lenguaje de la instrumentación de red en métricas, indicadores y estados compactos. Las vistas claras quedan reservadas para reportes, tablas extensas, exportaciones o consultas donde mejoren realmente la lectura; deben conservar la misma jerarquía, tipografía, espaciado y gramática de componentes. La experiencia nunca adopta recursos de landing page, marketing ni dashboard de BI decorativo.

**Key Characteristics:**

- Oscuro por defecto, con vistas claras excepcionales y coherentes.
- Alta densidad de información útil con jerarquía inequívoca.
- Estados operacionales reconocibles por color, texto e indicador.
- Componentes compactos, técnicos y contenidos.
- Decoración mínima; cada recurso visual debe ayudar a detectar, entender, priorizar o actuar.

## Colors

La paleta combina neutros casi negros con un azul de telemetría y colores de estado intensos, reservados para significado operacional. La vista clara usa blancos azulados y tinta índigo sin cambiar la gramática del sistema.

### Primary

- **Azul de Telemetría:** identifica selección, navegación activa, enlaces, foco y acciones operacionales.

### Secondary

- **Verde Operativo:** comunica estados positivos o conectividad cuando el módulo así lo define.
- **Amarillo de Señal:** destaca condiciones definidas por el contexto, como saturación uplink, errores CRC o temperatura elevada.
- **Naranja de Señal:** marca estados intermedios o elevados definidos por cada módulo.
- **Rojo de Alarma:** identifica caídas, alarmas o condiciones críticas según la semántica local.

### Neutral

- **Negro de Sala:** fondo dominante para supervisión prolongada.
- **Grafito de Consola:** superficie principal de paneles y tablas.
- **Acero de División:** bordes, separadores y rejillas de baja presencia.
- **Blanco Instrumental:** texto principal sobre superficies oscuras.
- **Gris de Contexto:** metadatos, etiquetas y explicaciones secundarias.
- **Blanco de Reporte:** superficie clara excepcional para vistas de lectura extensa.
- **Índigo de Lectura:** texto principal en superficies claras.

### Named Rules

**The Context Defines Meaning Rule.** El color no define por sí solo la severidad; el módulo y el estado operacional determinan su significado. La tabla principal y el módulo de temperatura tienen semánticas independientes.

**Tabla principal — Estado actual de red:**

- **Caída actual → rojo.** Badge rojo y valor resaltado en rojo.
- **Saturación uplink → amarillo.** Usa el badge general amarillo; no utiliza naranja.
- **Error CRC → amarillo.** Usa el badge general amarillo.

**Temperatura OLT:**

- **≥ 70 °C → amarillo.** Temperatura elevada.
- **≥ 80 °C → naranja.** Temperatura considerablemente elevada.
- **≥ 90 °C → rojo.** Temperatura extremadamente elevada.

**The Signal, Not Decoration Rule.** Los colores saturados se reservan para estados, alarmas, selección, foco y acciones importantes; nunca llenan grandes superficies con intención decorativa.

**The Redundancy Rule.** Ningún estado crítico depende únicamente del color: debe incluir texto, icono, etiqueta o indicador equivalente.

## Typography

**Display Font:** Segoe UI (con Inter y Arial como respaldo)
**Body Font:** Segoe UI (con Inter y Arial como respaldo)
**Label/Mono Font:** Segoe UI; no existe aún una familia monoespaciada normativa.

**Character:** Sans serif sobria, familiar en entornos operacionales y legible durante jornadas prolongadas. La jerarquía se apoya en peso, contraste y espaciado antes que en tamaños exagerados.

### Hierarchy

- **Headline** (700, 28px, 1.2): títulos principales de vista; compacto y funcional.
- **Title** (700, 18px, 1.25): encabezados de panel y nombres de módulos.
- **Body** (400, 14px, 1.5): contenido, ayudas y texto de lectura continua.
- **Label** (700, 11px, 0.055em): categorías, estados y metadatos breves; puede usar mayúsculas en rótulos de sección.
- **Data** (600–800, 12–16px): valores tabulares y métricas; se mantiene suficientemente compacto para comparar series.

### Named Rules

**The Operational Hierarchy Rule.** Una métrica importante gana jerarquía mediante contraste, peso y posición; el tamaño extremo no sustituye una estructura clara.

## Layout

La composición base usa una barra lateral estable de 220–230px y un área principal flexible con `min-width: 0`. Los paneles se organizan con CSS Grid; la vista principal usa dos columnas asimétricas y se convierte en una sola columna por debajo de 1180px. El ritmo observado se concentra en intervalos de 8, 12, 14, 16 y 24px.

Las tablas mantienen encabezados adherentes y desplazan únicamente su región interna cuando el ancho mínimo de datos no cabe. La página no debe producir overflow horizontal. En 700px o menos, el shell deja de ser lateral: la navegación ocupa el ancho disponible y los paneles se apilan. Las adaptaciones priorizan información crítica, estado operacional, acciones, contexto e información secundaria, en ese orden.

**The Controlled Density Rule.** Reducir espacios vacíos innecesarios sin mezclar grupos funcionales ni degradar la legibilidad.

**The Reflow Before Shrink Rule.** Reorganizar paneles y controles progresivamente antes de comprimir tipografía o contenido indiscriminadamente.

## Elevation & Depth

La profundidad se construye mediante capas tonales: fondo, sidebar, superficie, superficie secundaria, hover, selección y superposición. Los bordes sutiles ayudan a definir estructura. Las sombras ambientales fuertes no pertenecen a superficies en reposo; se reservan para modales, menús, popovers y paneles temporales realmente superpuestos. Los resplandores existentes se limitan a focos de estado pequeños y alarmas activas.

### Shadow Vocabulary

- **Sidebar separation** (`12px 0 40px rgba(0, 0, 0, .22)`): separa lateralmente la navegación fija cuando la composición lo necesita.
- **Active navigation** (`inset 3px 0 0 #27a4ff, 0 6px 18px rgba(0, 70, 130, .15)`): confirma la sección seleccionada sin hacerla flotar.
- **Status signal** (`0 0 10px rgba(21, 217, 122, .4)`): resplandor localizado exclusivamente alrededor de un indicador pequeño.
- **Overlay alarm** (`0 0 28px rgba(255, 48, 72, .6)`): reservado para alertas superpuestas que demandan interacción.

**The Tonal First Rule.** Una superficie en reposo obtiene jerarquía por tono y borde; la sombra sólo aparece cuando existe superposición o una señal operacional justificada.

## Shapes

El sistema usa geometría rectangular compacta con curvatura contenida. Controles y navegación emplean radios de 7–8px; paneles principales llegan a 12px; estados compactos usan 4px; contadores verdaderamente circulares usan 999px. Los bordes son finos y de bajo contraste. No se redondean todos los contenedores por defecto.

**The Contained Corners Rule.** La curvatura suaviza controles y paneles sin convertir la interfaz en una colección de tarjetas blandas o decorativas.

## Components

Los componentes son compactos, técnicos y contenidos. Sus estados deben preservar la semántica implementada en cada módulo.

### Buttons

- **Shape:** rectangular con esquinas contenidas (5–7px).
- **Primary:** el azul se reserva para acciones principales o selección; el padding típico es 8–14px.
- **Hover / Focus:** cambio tonal breve y foco visible de 2px; no usar animaciones expansivas.
- **Secondary / Ghost:** superficie oscura o transparente, texto claro y borde de acero.

### Chips

- **Style:** etiquetas compactas con fondo, texto y borde definidos por su contexto; radios de 4–7px.
- **State:** selección y severidad siempre incluyen texto. Los contadores pueden ser píldoras, pero los filtros no deben convertirse en decoración.

### Cards / Containers

- **Corner Style:** paneles principales con 10–12px; contenedores internos pueden usar 7–8px o permanecer planos.
- **Background:** capas de grafito ligeramente diferenciadas.
- **Shadow Strategy:** tonal por defecto; sombra sólo para superposición.
- **Border:** línea de 1px de bajo contraste.
- **Internal Padding:** 12–16px en paneles densos; 24px sólo cuando la jerarquía lo necesita.

### Inputs / Fields

- **Style:** fondo casi negro, borde de acero, texto claro y radio de 7px.
- **Focus:** borde azul y contorno visible; el foco no depende de un resplandor decorativo.
- **Error / Disabled:** acompañar color con texto o estado; mantener contraste y legibilidad.

### Navigation

- Barra lateral oscura y estable; íconos lineales consistentes, texto compacto y sección activa con capa azul, borde y acento lateral.
- Hover mediante cambio tonal corto. En pantallas pequeñas la navegación pasa a una retícula de dos columnas y oculta información secundaria del sidebar.

### Operational Tables

- Encabezados adherentes, filas compactas y separadores de bajo contraste.
- Resaltado de fila por cambio tonal; la severidad se expresa con etiqueta o texto además del color.
- El desplazamiento horizontal, cuando sea inevitable, queda contenido dentro de la tabla y nunca en la página.

### Status Indicators

- Puntos y barras son pequeños, localizados y acompañados por una etiqueta legible.
- La animación se reserva para una condición activa que demanda atención y debe respetar reducción de movimiento.

## Do's and Don'ts

### Do:

- **Do** usar el modo oscuro como identidad dominante para monitoreo continuo y operación intensiva.
- **Do** verificar el contexto del componente antes de interpretar o cambiar un color.
- **Do** conservar rojo para Caída actual y amarillo tanto para Saturación uplink como para Error CRC en la tabla principal.
- **Do** conservar los umbrales de temperatura OLT: amarillo desde 70 °C, naranja desde 80 °C y rojo desde 90 °C.
- **Do** usar texto, iconos o etiquetas junto al color para comunicar estados.
- **Do** reorganizar paneles según el ancho y mantener el overflow dentro de regiones de datos.
- **Do** reservar vistas claras para casos donde aporten una ventaja real de lectura.

### Don't:

- **Don't** imponer una escala global de severidad sobre módulos con semántica distinta.
- **Don't** trasladar la escala de temperatura a la tabla principal ni viceversa.
- **Don't** modificar reglas de negocio, endpoints, consultas o estructuras de datos para obtener consistencia visual.
- **Don't** usar sombras ambientales fuertes, glassmorphism, gradientes decorativos o tarjetas flotantes innecesarias.
- **Don't** llenar grandes áreas con colores saturados ni hacer que información secundaria compita con alarmas.
- **Don't** depender sólo del color, introducir animación distractora o sacrificar densidad útil por decoración.
