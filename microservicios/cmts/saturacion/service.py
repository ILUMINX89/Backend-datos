from collections import defaultdict
from datetime import datetime, timedelta, timezone
import logging
import math
import time
from typing import Any
from uuid import uuid4

from microservicios.cmts.saturacion.cache import (
    guardar_estado,
    guardar_saturacion,
)
from microservicios.cmts.saturacion.queries import obtener_muestras_flux
from microservicios.influx import iterar_flux_temp

UMBRAL_UTIL_SATURACION = 80.0
MIN_PUNTOS_SATURADOS = 100
MIN_UTIL_PROMEDIO = 50.0
SNR_UMBRAL_FISICO = 30.0
RATIO_MIN_DEGRADACION = 0.60
UMBRAL_CAPACIDAD_DEGRADADA = 80.0
BITS_POR_PORTADORA = 30_000_000
VENTANA_DIAS = 4
CHUNK_MINUTOS = 180
MAX_GAP_MINUTOS = 30
TOTAL_BLOQUES = VENTANA_DIAS * 24 * 60 // CHUNK_MINUTOS
VERSION_SATURACION = "2026-10-01-v2"

logger = logging.getLogger(__name__)


def _ahora() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _estado_base_ejecucion(ejecucion_id: str, iniciado_en: str) -> dict[str, Any]:
    return {
        "estado": "procesando",
        "ejecucion_id": ejecucion_id,
        "iniciado_en": iniciado_en,
        "finalizado_en": None,
        "error": None,
        "bloques_totales": TOTAL_BLOQUES,
        "chunk_minutos": CHUNK_MINUTOS,
        "ventana_dias": VENTANA_DIAS,
        "version_saturacion": VERSION_SATURACION,
    }


def iniciar_ejecucion_saturacion() -> dict[str, Any]:
    """Crea y publica el estado inicial aislado de una nueva ejecucion."""
    estado_base = _estado_base_ejecucion(uuid4().hex, _ahora())
    guardar_estado(
        {
            **estado_base,
            "fase": "iniciando",
            "bloque_actual": 0,
            "porcentaje": 0.0,
            "ultimo_bloque_en": None,
        }
    )
    return estado_base


def _valor_numerico(fila: dict[str, Any]) -> float | None:
    try:
        valor = float(fila["_value"])
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
    return valor if math.isfinite(valor) else None


def _nuevo_acumulado() -> dict[str, Any]:
    return {
        "muestras_analizadas": 0,
        "puntos_saturados": 0,
        "suma_util_saturados": 0.0,
        "puntos_con_falla": 0,
        "ultimo_bw": None,
        "ultima_fecha_bw": None,
        "bw_maximo_historico": 0.0,
        "portadoras": None,
        "ultima_fecha_portadoras": None,
        "ultimo_snr": None,
        "ultima_fecha_snr": None,
        "ultima_fecha_muestra": None,
    }


def _procesar_muestra(
    acumulado: dict[str, Any], fecha: datetime, muestra: dict[str, float]
) -> None:
    acumulado["ultima_fecha_muestra"] = fecha

    bw = muestra.get("bw")
    bw_valido = bw is not None and bw > 0
    if bw_valido:
        acumulado["ultimo_bw"] = bw
        acumulado["ultima_fecha_bw"] = fecha
        acumulado["bw_maximo_historico"] = max(acumulado["bw_maximo_historico"], bw)

    portadoras = muestra.get("portadoras")
    portadoras_validas = (
        portadoras is not None and portadoras > 0 and portadoras.is_integer()
    )
    if portadoras_validas:
        acumulado["portadoras"] = int(portadoras)
        acumulado["ultima_fecha_portadoras"] = fecha

    snr = muestra.get("snr")
    if snr is not None and snr > 0:
        acumulado["ultimo_snr"] = snr
        acumulado["ultima_fecha_snr"] = fecha

    utilizacion = muestra.get("utilizacion")
    porcentaje_uso = (
        utilizacion / bw * 100.0 if bw_valido and utilizacion is not None else None
    )

    if porcentaje_uso is not None and math.isfinite(porcentaje_uso):
        acumulado["muestras_analizadas"] += 1
        if porcentaje_uso >= UMBRAL_UTIL_SATURACION:
            acumulado["puntos_saturados"] += 1
            acumulado["suma_util_saturados"] += porcentaje_uso

            falla = False
            if snr is not None and snr > 0 and snr < SNR_UMBRAL_FISICO:
                falla = True
            elif bw_valido and portadoras_validas:
                capacidad_nominal = int(portadoras) * BITS_POR_PORTADORA
                if (bw / capacidad_nominal * 100.0) < UMBRAL_CAPACIDAD_DEGRADADA:
                    falla = True

            if falla:
                acumulado["puntos_con_falla"] += 1


def _resultado_puerto(
    puerto: str, descripcion: str, acumulado: dict[str, Any]
) -> dict[str, Any] | None:
    puntos_saturados = acumulado["puntos_saturados"]
    if puntos_saturados < MIN_PUNTOS_SATURADOS:
        return None

    util_promedio = acumulado["suma_util_saturados"] / puntos_saturados
    if util_promedio < MIN_UTIL_PROMEDIO:
        return None

    puntos_con_falla = acumulado["puntos_con_falla"]
    ratio_degradacion = puntos_con_falla / puntos_saturados

    estado = (
        "Degradación"
        if ratio_degradacion >= RATIO_MIN_DEGRADACION
        else "Saturación normal"
    )

    portadoras = acumulado["portadoras"]
    return {
        "puerto": descripcion,
        "puerto_fisico": puerto,
        "valor": round(max(0.0, min(100.0, util_promedio)), 2),
        "bw": acumulado["ultimo_bw"],
        "capacidad_nominal": (
            portadoras * BITS_POR_PORTADORA if portadoras is not None else None
        ),
        "bw_maximo_historico": acumulado["bw_maximo_historico"],
        "estado": estado,
        "tipo": "degradacion" if estado == "Degradación" else "uso",
        "puntos_sobre_80": puntos_saturados,
        "muestras_analizadas": acumulado["muestras_analizadas"],
        "ruido": acumulado["ultimo_snr"],
        "portadoras": portadoras,
        "ratio_degradacion": round(ratio_degradacion, 2),
    }


def _procesar_bloque(registros, acumulados: dict) -> None:
    # Solo se retienen campos asociados por clave de negocio y timestamp exacto.
    muestras_bloque: dict = {}
    for fila in registros:
        cmts, puerto, descripcion = (
            fila.get(campo) for campo in ("cmts", "puerto", "descripcion")
        )
        fecha = fila.get("_time")
        campo = fila.get("_field")
        valor = _valor_numerico(fila)
        if (
            not cmts
            or not puerto
            or not descripcion
            or not isinstance(fecha, datetime)
            or fecha.utcoffset() is None
            or campo not in ("bw", "utilizacion", "snr", "portadoras")
            or valor is None
        ):
            continue
        clave = (str(cmts), str(puerto), str(descripcion))
        muestras_bloque.setdefault(clave, {}).setdefault(fecha, {})[campo] = valor

    for clave, muestras in muestras_bloque.items():
        if clave not in acumulados:
            acumulados[clave] = _nuevo_acumulado()
        for fecha in sorted(muestras):
            _procesar_muestra(acumulados[clave], fecha, muestras[fecha])
    # Todas las referencias al bloque se liberan al retornar, antes de consultar otro.


def calcular_saturacion_actual(estado_base: dict[str, Any] | None = None) -> dict[str, Any]:
    """Evalua la ventana configurada mediante bloques secuenciales."""
    estado_base = estado_base or iniciar_ejecucion_saturacion()
    logger.info(
        "HFC: inicio ejecucion=%s ventana=%sd chunk=%smin bloques=%s version=%s",
        estado_base["ejecucion_id"],
        VENTANA_DIAS,
        CHUNK_MINUTOS,
        TOTAL_BLOQUES,
        VERSION_SATURACION,
    )
    logger.info("HFC: iniciando actualización")
    fin = datetime.now(timezone.utc)
    inicio = fin - timedelta(days=VENTANA_DIAS)
    acumulados: dict[tuple[str, str, str], dict[str, Any]] = {}

    for indice in range(TOTAL_BLOQUES):
        bloque_inicio = inicio + timedelta(minutes=indice * CHUNK_MINUTOS)
        bloque_fin = min(bloque_inicio + timedelta(minutes=CHUNK_MINUTOS), fin)
        _procesar_bloque(
            iterar_flux_temp(
                obtener_muestras_flux(bloque_inicio, bloque_fin), fuente="cmts"
            ),
            acumulados,
        )
        bloque_actual = indice + 1
        porcentaje = round(bloque_actual / TOTAL_BLOQUES * 100.0, 2)
        guardar_estado(
            {
                **estado_base,
                "estado": "procesando",
                "fase": "consultando_influx",
                "bloque_actual": bloque_actual,
                "bloques_totales": TOTAL_BLOQUES,
                "porcentaje": porcentaje,
                "ultimo_bloque_en": datetime.now()
                .astimezone()
                .isoformat(timespec="seconds"),
                "error": None,
            }
        )
        logger.info(
            "HFC: bloque %d/%d completado (%.2f%%)",
            bloque_actual,
            TOTAL_BLOQUES,
            porcentaje,
        )
        if bloque_actual < TOTAL_BLOQUES:
            time.sleep(0.05)

    guardar_estado(
        {
            **estado_base,
            "estado": "procesando",
            "fase": "analizando_resultados",
            "porcentaje": 100.0,
            "bloque_actual": TOTAL_BLOQUES,
            "bloques_totales": TOTAL_BLOQUES,
            "error": None,
        }
    )
    resultado: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (cmts, puerto, descripcion), acumulado in acumulados.items():
        item = _resultado_puerto(puerto, descripcion, acumulado)
        if item is not None:
            resultado[cmts].append(item)

    def criticidad(item: dict[str, Any]) -> tuple[int, float]:
        return (int(item["puntos_sobre_80"]), float(item["valor"]))

    datos = [
        {"cmts": cmts, "puertos": sorted(puertos, key=criticidad, reverse=True)}
        for cmts, puertos in resultado.items()
    ]
    datos.sort(key=lambda grupo: criticidad(grupo["puertos"][0]), reverse=True)
    logger.info("HFC: puertos evaluados=%d", len(acumulados))
    logger.info(
        "HFC: puertos confirmados=%d", sum(len(grupo["puertos"]) for grupo in datos)
    )
    return {"datos": datos}


def actualizar_saturacion(estado_base: dict[str, Any] | None = None) -> dict[str, Any]:
    """Reemplaza el cache solamente después de finalizar correctamente."""
    estado_base = estado_base or iniciar_ejecucion_saturacion()
    resultado = calcular_saturacion_actual(estado_base)
    cache = {
        "generado_en": datetime.now().astimezone().isoformat(timespec="seconds"),
        "ventana": "4d",
        "datos": resultado["datos"],
    }
    guardar_saturacion(cache)
    guardar_estado(
        {
            **estado_base,
            "estado": "listo",
            "fase": "finalizado",
            "bloque_actual": TOTAL_BLOQUES,
            "porcentaje": 100.0,
            "ultimo_bloque_en": _ahora(),
            "finalizado_en": _ahora(),
        }
    )
    logger.info("HFC: cache actualizado")
    return cache
