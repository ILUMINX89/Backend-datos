"""Calculo y persistencia de la saturacion actual CMTS."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import logging
import math
import time
from typing import Any

from microservicios.cmts.saturacion.cache import guardar_saturacion
from microservicios.cmts.saturacion.queries import obtener_bw_flux, obtener_snr_flux, obtener_utilizacion_flux
from microservicios.influx import consultar_flux_temp

MUESTRAS_CONFIRMACION_SNR = 60
UMBRAL_UTILIZACION = 90.0
UMBRAL_SNR_DEGRADADO_DB = 30.0
VENTANA_DIAS = 4
CHUNK_HORAS = 6
logger = logging.getLogger(__name__)


def _agrupar_snr(filas: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    resultado: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for fila in filas:
        cmts = fila.get("cmts")
        descripcion = fila.get("descripcion")
        if cmts and descripcion and fila.get("_value") is not None:
            resultado[(str(cmts), str(descripcion))].append(fila)
    for muestras in resultado.values():
        muestras.sort(key=lambda fila: fila.get("_time"), reverse=True)
    return dict(resultado)


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
    bw_por_puerto: dict[tuple[str, str], float] = {}
    for fila in consultar_flux_temp(obtener_bw_flux(), fuente="cmts"):
        bw = _valor_numerico(fila, "_value")
        if fila.get("cmts") and fila.get("descripcion") and bw is not None and math.isfinite(bw) and bw > 0:
            bw_por_puerto[(str(fila["cmts"]), str(fila["descripcion"]))] = bw
    logger.info("HFC: BW cargado")

    acumulados: dict[tuple[str, str], dict[str, float | int]] = {}
    total_bloques = VENTANA_DIAS * 24 // CHUNK_HORAS
    for indice in range(total_bloques):
        bloque_inicio = inicio + timedelta(hours=indice * CHUNK_HORAS)
        bloque_fin = min(bloque_inicio + timedelta(hours=CHUNK_HORAS), fin)
        filas = consultar_flux_temp(obtener_utilizacion_flux(bloque_inicio, bloque_fin), fuente="cmts")
        for fila in filas:
            clave = (str(fila.get("cmts") or ""), str(fila.get("descripcion") or ""))
            bw = bw_por_puerto.get(clave)
            utilizacion = _valor_numerico(fila, "_value")
            if bw is None or utilizacion is None or not math.isfinite(utilizacion):
                continue
            porcentaje = max(0.0, min(100.0, utilizacion / bw * 100.0))
            acumulado = acumulados.setdefault(clave, {
                "muestras_analizadas": 0, "puntos_sobre_90": 0,
                "suma_sobre_90": 0.0, "suma_total": 0.0,
            })
            acumulado["muestras_analizadas"] += 1
            acumulado["suma_total"] += porcentaje
            if porcentaje >= UMBRAL_UTILIZACION:
                acumulado["puntos_sobre_90"] += 1
                acumulado["suma_sobre_90"] += porcentaje
        logger.info("HFC: bloque utilización %d/%d completado", indice + 1, total_bloques)
        if indice + 1 < total_bloques:
            time.sleep(0.5)

    muestras_snr = _agrupar_snr(consultar_flux_temp(obtener_snr_flux(), fuente="cmts"))
    logger.info("HFC: SNR cargado")
    resultado: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for (cmts, descripcion), acumulado in acumulados.items():
        bw = bw_por_puerto[(cmts, descripcion)]
        muestras_analizadas = int(acumulado["muestras_analizadas"])
        puntos_sobre_90 = int(acumulado["puntos_sobre_90"])
        promedio_umbral = acumulado["suma_sobre_90"] / puntos_sobre_90 if puntos_sobre_90 else None
        promedio_total = acumulado["suma_total"] / muestras_analizadas if muestras_analizadas else None

        valores_ruido: list[float] = []
        for muestra in muestras_snr.get((cmts, descripcion), []):
            valor = _valor_numerico(muestra, "_value")
            if valor is None or valor <= 0:
                break
            valores_ruido.append(valor)

        uso_confirmado = puntos_sobre_90 > 0
        degradacion_confirmada = (
            len(valores_ruido) == MUESTRAS_CONFIRMACION_SNR
            and all(valor < UMBRAL_SNR_DEGRADADO_DB for valor in valores_ruido)
        )
        if not uso_confirmado and not degradacion_confirmada:
            continue
        porcentaje = promedio_umbral if uso_confirmado else promedio_total
        if porcentaje is None:
            continue
        porcentaje = max(0.0, min(100.0, porcentaje))
        resultado[cmts].append({
            "puerto": descripcion, "valor": round(porcentaje, 2), "bw": bw,
            "estado": "Saturación por degradación" if degradacion_confirmada else "Saturación",
            "tipo": "degradacion" if degradacion_confirmada else "uso",
            "puntos_sobre_90": puntos_sobre_90,
            "muestras_analizadas": muestras_analizadas,
            "ruido": valores_ruido[0] if valores_ruido else None,
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
