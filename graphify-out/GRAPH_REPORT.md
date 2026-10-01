# Graph Report - Backend-datos  (2026-10-01)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1117 nodes · 3018 edges · 79 communities (48 shown, 1 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 98 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4605b856`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48

## God Nodes (most connected - your core abstractions)
1. `resumeSession()` - 32 edges
2. `setLiveState()` - 32 edges
3. `connectSSE()` - 31 edges
4. `showToast()` - 30 edges
5. `initGlobalBar()` - 29 edges
6. `el()` - 29 edges
7. `handleKeyDown()` - 27 edges
8. `injectSvelteComponentsFromManifest()` - 26 edges
9. `cleanup()` - 26 edges
10. `buildInsertConfigureRow()` - 26 edges

## Surprising Connections (you probably didn't know these)
- `exportar_csv()` --indirect_call--> `archivo()`  [INFERRED]
  probar_cmts.py → microservicios/olt/topologias/router.py
- `Filtra el umbral despues de seleccionar la ultima muestra de cada puerto.` --rationale_for--> `obtener_saturacion_actual_flux()`  [EXTRACTED]
  microservicios/olt/crc/queries.py → microservicios/olt/saturacion/queries.py
- `main()` --indirect_call--> `obtener_saturacion()`  [INFERRED]
  microservicios/consultar_influx.py → microservicios/olt/saturacion/service.py
- `layoutFlowChildren()` --indirect_call--> `pickable()`  [INFERRED]
  .agents/skills/impeccable/scripts/live-browser.js → .agents/skills/impeccable/scripts/live-browser-dom.js
- `_guardar_atomico()` --indirect_call--> `archivo()`  [INFERRED]
  microservicios/cmts/saturacion/cache.py → microservicios/olt/topologias/router.py

## Import Cycles
- None detected.

## Communities (79 total, 1 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.04
Nodes (68): applyGlobalBarLabelState(), buildInsertPlaceholderSnapshotFromDom(), buildLocatorForLeaf(), buildPickedAnchorSnapshot(), buildPlaceholderResizeHandles(), buildSavingRow(), buildSteerQueueHint(), checkpointPayload() (+60 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (62): agentHasWorkInFlight(), agentStatusText(), barPaletteForTheme(), brandMarkSvg(), buildDesignHeader(), clearStoredManualApplyState(), designPanelCss(), detectPageTheme() (+54 more)

### Community 2 - "Community 2"
Cohesion: 0.09
Nodes (58): FileResponse, archivo(), _buscar(), buscar_global(), ftto(), health(), huawei(), imagen() (+50 more)

### Community 3 - "Community 3"
Cohesion: 0.09
Nodes (55): ae(), be(), bt(), Ce(), s(), Ct(), de(), dt() (+47 more)

### Community 4 - "Community 4"
Cohesion: 0.09
Nodes (47): BackgroundTasks, _guardar_atomico(), guardar_estado(), guardar_saturacion(), _leer(), leer_estado(), leer_saturacion(), Any (+39 more)

### Community 5 - "Community 5"
Cohesion: 0.09
Nodes (47): armPageChatForTyping(), attachSteerFocusDebug(), attachSteerFocusGuard(), buildSteerProcessingDots(), clearSteerAwaitTimer(), clearSteerFocusRecoverTimer(), collapsePageChat(), expandPageChat() (+39 more)

### Community 6 - "Community 6"
Cohesion: 0.09
Nodes (44): actionLabel(), bindConfigureCountPillTooltip(), bindConfigureInlineControlHover(), bindConfigureModifierPillHover(), buildConfigureActionControl(), buildConfigureCountControl(), buildConfigureRow(), buildConfigureSubmitButton() (+36 more)

### Community 7 - "Community 7"
Cohesion: 0.07
Nodes (31): exception_handler, JSONResponse, error_http(), error_no_controlado(), error_validacion(), health(), Exception, get (+23 more)

### Community 8 - "Community 8"
Cohesion: 0.08
Nodes (36): buildCollapsible(), buildColorModels(), buildListHtml(), buildRadiiModels(), buildTypographyModels(), copyToClipboard(), cssSafe(), designEmptyMessage() (+28 more)

### Community 9 - "Community 9"
Cohesion: 0.20
Nodes (33): applyEditing(), beginNewLiveConfiguration(), cancelEditing(), cancelEditingToPicking(), cancelInsertConfigure(), clearAnnotations(), clearInsertPicking(), disableInlineEdit() (+25 more)

### Community 10 - "Community 10"
Cohesion: 0.13
Nodes (33): applySavedSessionMeta(), clearHandled(), commitAcceptedVariantToDom(), cycleVariant(), ensureInsertPlaceholder(), enterRecoveryWaitingForAnchor(), finalizeInsertSession(), findAnyVariantsWrapper() (+25 more)

### Community 11 - "Community 11"
Cohesion: 0.08
Nodes (32): addManualContextText(), canRestoreManualEditElement(), collectManualContextPieces(), walk(), contextElementForManualEdit(), copyEditContainerContext(), copyEditLeafContext(), cssIdent() (+24 more)

### Community 12 - "Community 12"
Cohesion: 0.17
Nodes (25): _escapar_flux(), obtener_caidas_flux(), obtener_estado_actual_flux(), obtener_ultima_actividad_flux(), obtener_ultima_muestra_conocida_flux(), Consultas Flux para detectar caídas de puertos OLT por tráfico., Obtiene las últimas muestras de tráfico recientes. Se revisan 30 minutos para…, Obtiene la última muestra conocida de cada puerto. Sirve para detectar puertos… (+17 more)

### Community 13 - "Community 13"
Cohesion: 0.20
Nodes (25): abandonForeignSession(), completeParameterGenerationIfReady(), completeParameterPublication(), completeSourceInjection(), connectSSE(), discardOrphanedSession(), dismissToast(), handleAccept() (+17 more)

### Community 14 - "Community 14"
Cohesion: 0.12
Nodes (23): applyOriginalAttrsToSvelteAnchor(), captureAndEmit(), commitAcceptedSvelteComponentToDom(), componentModuleCandidates(), describeMountFailure(), detectDevServerBase(), findInsertAnchorInDom(), findLiveElementForSvelteManifest() (+15 more)

### Community 15 - "Community 15"
Cohesion: 0.11
Nodes (23): averageRgb01(), bufferToBase64(), captureChromeNodes(), captureElementFromRenderedAncestor(), captureElementToBlob(), collectFontCssText(), compileShader(), cssColorToRgb01() (+15 more)

### Community 16 - "Community 16"
Cohesion: 0.14
Nodes (22): applyPlaceholderDimensions(), beginEditPin(), buildAnnotationsForCapture(), buildPinElement(), cancelEditingPin(), clampPlaceholderSize(), finalizeEditingPin(), initAnnotOverlay() (+14 more)

### Community 17 - "Community 17"
Cohesion: 0.16
Nodes (19): Devuelve los puertos cuya ultima muestra supera el umbral actual., _metricas_saturacion_flux(), obtener_saturacion_actual_flux(), obtener_saturacion_flux(), Consultas Flux para saturacion de puertos OLT., Devuelve la secuencia de muestras con saturacion superior al 70 %., get, Rutas HTTP de saturacion OLT. (+11 more)

### Community 18 - "Community 18"
Cohesion: 0.12
Nodes (15): collectEditableTextRows(), visit(), createLiveBrowserDomHelpers(), cssId(), liveUiRoot(), makeFrozenAnchor(), own(), pickable() (+7 more)

### Community 19 - "Community 19"
Cohesion: 0.23
Nodes (19): api_route, _configuration_ready(), _ensure_authenticated_locked(), _is_login_redirect(), _login_locked(), proxy(), proxy_health(), _proxy_locked() (+11 more)

### Community 20 - "Community 20"
Cohesion: 0.18
Nodes (16): _metricas_crc_flux(), obtener_crc_actual_flux(), obtener_crc_flux(), Consultas Flux para errores CRC de puertos OLT., Devuelve muestras superiores a diez errores CRC por segundo., Filtra el umbral despues de seleccionar la ultima muestra de cada puerto., crc(), crc_actual() (+8 more)

### Community 21 - "Community 21"
Cohesion: 0.16
Nodes (19): buildSvelteExpressionTextMap(), buildSveltePropValuesFromLiveElement(), buildSveltePropValuesV2(), cloneWithoutElements(), collectTextNodes(), collectVisibleTexts(), cssEscapeIdent(), elementMatchesOriginalMarkup() (+11 more)

### Community 22 - "Community 22"
Cohesion: 0.21
Nodes (15): createLiveBrowserSessionState(), clearHandled(), clearScrollY(), clearSession(), isHandled(), loadSession(), markHandled(), nextCheckpointRevision() (+7 more)

### Community 23 - "Community 23"
Cohesion: 0.24
Nodes (16): changeDays(), changePanel(), checkUpdateStatus(), compareCriticality(), eyeButton(), formatUpdatedAt(), grafanaUrl(), load() (+8 more)

### Community 24 - "Community 24"
Cohesion: 0.25
Nodes (16): abortSvelteComponentInjection(), cleanup(), cleanupAcceptedSession(), clearMountErrorCard(), clearScrollY(), clearSession(), recoverEmptyCycling(), removeVariantStateStylesheet() (+8 more)

### Community 25 - "Community 25"
Cohesion: 0.13
Nodes (16): applyPlaceholderSizingStyles(), createInsertPlaceholder(), cursorForInsertAxis(), detectInsertAxis(), detectInsertAxisFromStyle(), ensureInsertLine(), handleMouseMove(), hideHighlightTagTooltip() (+8 more)

### Community 26 - "Community 26"
Cohesion: 0.19
Nodes (13): obtener_intermitencias_flux(), Consultas Flux para detectar intermitencias HFC., Detecta caídas de puertos HFC usando cm_registrados. Una caída se confirma…, intermitencias_actual(), get, Rutas HTTP de intermitencias HFC., _numero_entero(), obtener_intermitencias_actuales() (+5 more)

### Community 27 - "Community 27"
Cohesion: 0.19
Nodes (13): obtener_puertos_duplicados_flux(), Consultas Flux para detectar nodos en puertos CMTS duplicados., Obtiene la ubicacion mas reciente de cada descripcion, CMTS y puerto., puertos_duplicados_actual(), get, Rutas HTTP de nodos asociados a multiples puertos CMTS., normalizar_descripcion(), obtener_puertos_duplicados_actuales() (+5 more)

### Community 28 - "Community 28"
Cohesion: 0.22
Nodes (15): applyParamDefaults(), applyParamValue(), buildParamsPanel(), closedClipPath(), closeTunePopover(), hideParamsPanel(), mountedParameterCount(), openTunePopover() (+7 more)

### Community 29 - "Community 29"
Cohesion: 0.31
Nodes (13): alertIdentity(), closeFtthModal(), connection(), formatValue(), ftthGrafanaUrl(), load(), loadFtthFrame(), monitoring() (+5 more)

### Community 30 - "Community 30"
Cohesion: 0.33
Nodes (11): badgeClass(), closeTemperatureModal(), formatTemperature(), loadTemperature(), loadTemperatureChart(), openTemperatureModal(), renderTemperature(), setTemperatureRange() (+3 more)

### Community 31 - "Community 31"
Cohesion: 0.33
Nodes (11): ejecutar_caidas(), ejecutar_intermitencias(), imprimir_resultado(), main(), mostrar_menu(), Any, Herramienta interactiva para probar manualmente los servicios OLT., seleccionar_periodo_caidas() (+3 more)

### Community 32 - "Community 32"
Cohesion: 0.24
Nodes (9): obtener_temperatura_actual_flux(), Consulta de temperatura actual por tarjeta OLT., get, Rutas HTTP de temperatura OLT., temperatura_actual(), clasificar_temperatura(), obtener_temperatura_actual(), Any (+1 more)

### Community 33 - "Community 33"
Cohesion: 0.27
Nodes (4): datosClient(), jsonResponse(), requireMethod(), MicroserviceClient

### Community 34 - "Community 34"
Cohesion: 0.35
Nodes (10): InfluxDBClient, consultar_flux_temp(), crear_cliente_cmts(), crear_cliente_temp(), iterar_flux_temp(), probar_conexion_temp(), Any, Cliente InfluxDB para Trafico Temperatura OLTs. (+2 more)

### Community 35 - "Community 35"
Cohesion: 0.25
Nodes (9): correlacion(), get, Rutas HTTP de correlacion OLT., eventos_se_relacionan(), obtener_correlacion(), Any, Correlacion temporal de saturacion, CRC y caidas OLT., Indica si dos intervalos se cruzan dentro del margen configurado. (+1 more)

### Community 36 - "Community 36"
Cohesion: 0.29
Nodes (10): acceptedDomAlreadyClean(), clearHandledWrapperReloadStamp(), deferredRecoverySuperseded(), ensureAcceptedDomClean(), findAcceptedRuntimeWrappers(), handledWrapperReloadKey(), reloadAfterMissingAcceptedDom(), restoreAcceptedDomFromSnapshot() (+2 more)

### Community 37 - "Community 37"
Cohesion: 0.33
Nodes (10): applyConfigureBarChrome(), buildCyclingRow(), cyclingCounterText(), cyclingShownVariant(), ensureCyclingRenderable(), restorePickerBarChrome(), scheduleCyclingBarSync(), showBar() (+2 more)

### Community 38 - "Community 38"
Cohesion: 0.27
Nodes (10): bindEditBadgeProxy(), editBadgeProxyTargets(), initEditBadge(), initEditBadgeHitProxies(), positionEditBadge(), proxyMouseEvent(), setImportantStyle(), styleEditBadgeProxy() (+2 more)

### Community 39 - "Community 39"
Cohesion: 0.53
Nodes (8): esperar_puerto(), iniciar_tunel(), iniciar_uvicorn(), main(), matar(), nueva_consola_kwargs(), puerto_abierto(), Popen

### Community 40 - "Community 40"
Cohesion: 0.36
Nodes (7): caidas(), caidas_actuales(), intermitencias(), get, Rutas HTTP de caídas e intermitencias OLT., obtener_intermitencias(), Detecta puertos intermitentes reutilizando las mismas caídas históricas. Regla:…

### Community 41 - "Community 41"
Cohesion: 0.43
Nodes (7): consultar(), convertir_visio_a_jpg(), main(), obtener_ruta_local(), procesar_mensajes(), Prueba manual de la API de topologías OLT con conversión VSD/VSDX -> JPG., recortar_imagen()

### Community 42 - "Community 42"
Cohesion: 0.50
Nodes (7): convertir_individual(), convertir_masivo(), convertir_visio_a_jpg(), main(), obtener_archivos_visio(), procesar_mensajes(), recortar_imagen()

### Community 43 - "Community 43"
Cohesion: 0.52
Nodes (6): globToRegex(), matchesScope(), normalizeIgnoreRule(), normalizeIgnoreValue(), pageCandidates(), resolveDetectIgnores()

### Community 44 - "Community 44"
Cohesion: 0.60
Nodes (5): impeccable script, check_download(), fetch_url(), probe_ok(), setup_help()

### Community 45 - "Community 45"
Cohesion: 0.53
Nodes (4): frame(), hold(), resetAll(), scrollToTop()

### Community 46 - "Community 46"
Cohesion: 0.50
Nodes (4): BaseSettings, get_settings(), Configuracion comun de los microservicios., Settings

### Community 47 - "Community 47"
Cohesion: 0.83
Nodes (3): formatNumber(), load(), render()

## Knowledge Gaps
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `consultar_flux_temp()` connect `Community 34` to `Community 32`, `Community 12`, `Community 17`, `Community 20`, `Community 26`, `Community 27`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Why does `enableInlineEdit()` connect `Community 18` to `Community 0`, `Community 9`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `initGlobalBar()` (e.g. with `hideAgentPollTooltip()` and `onDetectMessage()`) actually correct?**
  _`initGlobalBar()` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.043478260869565216 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.06547619047619048 - nodes in this community are weakly interconnected._
- **Should `Community 2` be split into smaller, more focused modules?**
  _Cohesion score 0.09011776753712238 - nodes in this community are weakly interconnected._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.08959899749373433 - nodes in this community are weakly interconnected._