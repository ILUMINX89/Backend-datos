"""Calculo y persistencia de la saturacion actual CMTS."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import logging
import math
import time
from typing import Any

from microservicios.cmts.saturacion.cache import guardar_saturacion
from microservicios.cmts.saturacion.queries import obtener_bw_flux, obtener_utilizacion_flux
from microservicios.influx import consultar_flux_temp

MIN_PUNTOS_SATURACION = 100
UMBRAL_UTILIZACION = 90.0
UMBRAL_CAPACIDAD_DEGRADADA = 80.0
VENTANA_DIAS = 4
CHUNK_HORAS = 6
logger = logging.getLogger(__name__)


def _valor_numerico(fila: dict[str, Any], campo: str) -> float | None:
    try:
        return float(fila[campo])
    except (KeyError, TypeError, ValueError):
        return None


def calcular_saturacion_actual() -> dict[str, Any]:
    """Consulta secuencialmente y agrega la utilizacion en Python."""
    logger.info("HFC: iniciando actualización")
    fin = datetime.now(timezone.utc)
    inicio = fin - timedelta(days=VENTANA_DIAS)
    # Una sola lectura de BW: último valor por fecha y máximo de la ventana.
    bw_por_puerto: dict[tuple[str, str], tuple[datetime, float, float]] = {}
    for fila in consultar_flux_temp(obtener_bw_flux(), fuente="cmts"):
        bw = _valor_numerico(fila, "_value")
        fecha = fila.get("_time")
        if not (fila.get("cmts") and fila.get("descripcion") and isinstance(fecha, datetime)
                and bw is not None and math.isfinite(bw) and bw > 0):
            continue
        clave = (str(fila["cmts"]), str(fila["descripcion"]))
        anterior = bw_por_puerto.get(clave)
        if anterior is None:
            bw_por_puerto[clave] = (fecha, bw, bw)
        else:
            fecha_actual, capacidad_actual, capacidad_normal = anterior
            if fecha > fecha_actual:
                fecha_actual, capacidad_actual = fecha, bw
            bw_por_puerto[clave] = (fecha_actual, capacidad_actual, max(capacidad_normal, bw))
    umbrales: dict[tuple[str, str], tuple[float, bool]] = {}
    for clave, (_, actual, normal) in bw_por_puerto.items():
        porcentaje_capacidad = actual / normal * 100.0
        degradado = porcentaje_capacidad < UMBRAL_CAPACIDAD_DEGRADADA
        umbral = UMBRAL_UTILIZACION - (100.0 - porcentaje_capacidad) if degradado else UMBRAL_UTILIZACION
        umbrales[clave] = (umbral, degradado)
    logger.info("HFC: BW cargado")

    acumulados: dict[tuple[str, str], dict[str, float | int]] = {}
    total_bloques = VENTANA_DIAS * 24 // CHUNK_HORAS
    for indice in range(total_bloques):
        bloque_inicio = inicio + timedelta(hours=indice * CHUNK_HORAS)
        bloque_fin = min(bloque_inicio + timedelta(hours=CHUNK_HORAS), fin)
        filas = consultar_flux_temp(obtener_utilizacion_flux(bloque_inicio, bloque_fin), fuente="cmts")
        for fila in filas:
            clave = (str(fila.get("cmts") or ""), str(fila.get("descripcion") or ""))
            capacidad = bw_por_puerto.get(clave)
            utilizacion = _valor_numerico(fila, "_value")
            if capacidad is None or utilizacion is None or not math.isfinite(utilizacion):
                continue
            porcentaje = max(0.0, min(100.0, utilizacion / capacidad[1] * 100.0))
            acumulado = acumulados.setdefault(clave, {
                "muestras_analizadas": 0, "puntos_sobre_90": 0,
                "suma_sobre_90": 0.0,
            })
            acumulado["muestras_analizadas"] += 1
            if porcentaje >= umbrales[clave][0]:
                acumulado["puntos_sobre_90"] += 1
                acumulado["suma_sobre_90"] += porcentaje
        logger.info("HFC: bloque utilización %d/%d completado", indice + 1, total_bloques)
        if indice + 1 < total_bloques:
            time.sleep(0.5)

    resultado: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for (cmts, descripcion), acumulado in acumulados.items():
        bw = bw_por_puerto[(cmts, descripcion)][1]
        muestras_analizadas = int(acumulado["muestras_analizadas"])
        puntos_sobre_90 = int(acumulado["puntos_sobre_90"])
        if puntos_sobre_90 < MIN_PUNTOS_SATURACION:
            continue
        porcentaje = acumulado["suma_sobre_90"] / puntos_sobre_90
        porcentaje = max(0.0, min(100.0, porcentaje))
        degradado = umbrales[(cmts, descripcion)][1]
        resultado[cmts].append({
            "puerto": descripcion, "valor": round(porcentaje, 2), "bw": bw,
            "estado": "Saturación por degradación" if degradado else "Saturación",
            "tipo": "degradacion" if degradado else "uso",
            "puntos_sobre_90": puntos_sobre_90,
            "muestras_analizadas": muestras_analizadas,
            "ruido": None,
        })

    def criticidad(item: dict[str, Any]) -> tuple[int, float]:
        return int(item["puntos_sobre_90"]), float(item["valor"])

    datos = [
        {"cmts": cmts, "puertos": sorted(puertos, key=criticidad, reverse=True)}
        for cmts, puertos in resultado.items()
    ]
    datos.sort(key=lambda grupo: criticidad(grupo["puertos"][0]), reverse=True)
    return {"datos": datos}


def actualizar_saturacion() -> dict[str, Any]:
    """Calcula y reemplaza el cache solo después de finalizar correctamente."""
    resultado = calcular_saturacion_actual()
    cache = {
        "generado_en": datetime.now().astimezone().isoformat(timespec="seconds"),
        "ventana": "4d", "datos": resultado["datos"],
    }
    guardar_saturacion(cache)
    logger.info("HFC: cache actualizado")
    return cache
