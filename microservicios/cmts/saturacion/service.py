from collections import defaultdict
from datetime import datetime, timedelta, timezone
import logging
import math
import time
from typing import Any

from microservicios.cmts.saturacion.cache import (
    guardar_estado,
    guardar_saturacion,
    leer_estado,
)
from microservicios.cmts.saturacion.queries import obtener_muestras_flux
from microservicios.influx import iterar_flux_temp

UMBRAL_UTILIZACION = 80.0
UMBRAL_CAPACIDAD_DEGRADADA = 80.0
UMBRAL_SNR_DEGRADADO_DB = 30.0
MUESTRAS_CONFIRMACION_USO = 100
MUESTRAS_CONFIRMACION_CAPACIDAD = 100
MUESTRAS_CONFIRMACION_SNR = 60
BITS_POR_PORTADORA = 30_000_000
VENTANA_DIAS = 4
CHUNK_MINUTOS = 30
MAX_GAP_MINUTOS = 15
TOTAL_BLOQUES = VENTANA_DIAS * 24 * 60 // CHUNK_MINUTOS

logger = logging.getLogger(__name__)


def _valor_numerico(fila: dict[str, Any]) -> float | None:
    try:
        valor = float(fila["_value"])
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
    return valor if math.isfinite(valor) else None


def _nuevo_acumulado() -> dict[str, Any]:
    return {
        "muestras_analizadas": 0,
        "puntos_sobre_80": 0,
        "suma_sobre_80": 0.0,
        "racha_uso_actual": 0,
        "racha_uso_maxima": 0,
        "racha_capacidad_actual": 0,
        "racha_capacidad_maxima": 0,
        "racha_snr_actual": 0,
        "racha_snr_maxima": 0,
        "ultimo_bw": None,
        "ultima_fecha_bw": None,
        "bw_maximo_historico": 0.0,
        "portadoras": None,
        "ultima_fecha_portadoras": None,
        "ultimo_snr": None,
        "ultima_fecha_snr": None,
        "ultima_fecha_muestra": None,
        "muestras_snr_validas": 0,
        "muestras_capacidad_degradada": 0,
        "puntos_saturacion_degradada": 0,
    }


def _procesar_muestra(acumulado: dict[str, Any], fecha: datetime,
                      muestra: dict[str, float]) -> None:
    anterior = acumulado["ultima_fecha_muestra"]
    if anterior is not None and fecha - anterior > timedelta(minutes=MAX_GAP_MINUTOS):
        for criterio in ("uso", "capacidad", "snr"):
            acumulado[f"racha_{criterio}_actual"] = 0
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

    utilizacion = muestra.get("utilizacion")
    porcentaje_uso = utilizacion / bw * 100.0 if bw_valido and utilizacion is not None else None
    uso_alto = False
    if porcentaje_uso is not None and math.isfinite(porcentaje_uso):
        acumulado["muestras_analizadas"] += 1
        uso_alto = porcentaje_uso > UMBRAL_UTILIZACION
        if uso_alto:
            acumulado["puntos_sobre_80"] += 1
            acumulado["suma_sobre_80"] += porcentaje_uso

    capacidad_degradada = False
    if bw_valido and portadoras_validas:
        capacidad_nominal = int(portadoras) * BITS_POR_PORTADORA
        capacidad_degradada = bw / capacidad_nominal * 100.0 < UMBRAL_CAPACIDAD_DEGRADADA
        if capacidad_degradada:
            acumulado["muestras_capacidad_degradada"] += 1
            acumulado["puntos_saturacion_degradada"] += int(uso_alto)

    snr = muestra.get("snr")
    snr_degradado = False
    if snr is not None and snr > 0:
        acumulado["muestras_snr_validas"] += 1
        acumulado["ultimo_snr"] = snr
        acumulado["ultima_fecha_snr"] = fecha
        snr_degradado = snr < UMBRAL_SNR_DEGRADADO_DB

    # Un dato insuficiente rompe solo la racha del criterio correspondiente.
    for criterio, cumple in (("uso", uso_alto), ("capacidad", capacidad_degradada),
                             ("snr", snr_degradado)):
        actual = f"racha_{criterio}_actual"
        maxima = f"racha_{criterio}_maxima"
        acumulado[actual] = acumulado[actual] + 1 if cumple else 0
        acumulado[maxima] = max(acumulado[maxima], acumulado[actual])


def _resultado_puerto(puerto: str, descripcion: str,
                      acumulado: dict[str, Any]) -> dict[str, Any] | None:
    uso_confirmado = acumulado["racha_uso_maxima"] >= MUESTRAS_CONFIRMACION_USO
    degradacion_capacidad = acumulado["racha_capacidad_maxima"] >= MUESTRAS_CONFIRMACION_CAPACIDAD
    degradacion_snr = acumulado["racha_snr_maxima"] >= MUESTRAS_CONFIRMACION_SNR
    degradacion_confirmada = degradacion_capacidad or degradacion_snr
    if not uso_confirmado and not degradacion_confirmada:
        return None

    if uso_confirmado:
        estado = "Saturación por degradación" if degradacion_confirmada else "Saturación"
    else:
        estado = "Degradación"
    puntos = acumulado["puntos_sobre_80"]
    porcentaje = acumulado["suma_sobre_80"] / puntos if puntos else 0.0
    portadoras = acumulado["portadoras"]
    return {
        "puerto": descripcion,
        "puerto_fisico": puerto,
        "valor": round(max(0.0, min(100.0, porcentaje)), 2),
        "bw": acumulado["ultimo_bw"],
        "capacidad_nominal": portadoras * BITS_POR_PORTADORA if portadoras is not None else None,
        "bw_maximo_historico": acumulado["bw_maximo_historico"],
        "estado": estado,
        "tipo": "degradacion" if degradacion_confirmada else "uso",
        "puntos_sobre_80": puntos,
        "muestras_analizadas": acumulado["muestras_analizadas"],
        "puntos_saturacion_degradada": acumulado["puntos_saturacion_degradada"],
        "ruido": acumulado["ultimo_snr"],
        "portadoras": portadoras,
        "racha_uso_maxima": acumulado["racha_uso_maxima"],
        "racha_capacidad_maxima": acumulado["racha_capacidad_maxima"],
        "racha_snr_maxima": acumulado["racha_snr_maxima"],
        "degradacion_capacidad": degradacion_capacidad,
        "degradacion_snr": degradacion_snr,
    }


def _procesar_bloque(registros, acumulados: dict) -> None:
    # Solo se retienen campos asociados por clave de negocio y timestamp exacto.
    muestras_bloque: dict = {}
    for fila in registros:
        cmts, puerto, descripcion = (fila.get(campo) for campo in ("cmts", "puerto", "descripcion"))
        fecha = fila.get("_time")
        campo = fila.get("_field")
        valor = _valor_numerico(fila)
        if (not cmts or not puerto or not descripcion
                or not isinstance(fecha, datetime) or fecha.utcoffset() is None
                or campo not in ("bw", "utilizacion", "snr", "portadoras") or valor is None):
            continue
        clave = (str(cmts), str(puerto), str(descripcion))
        muestras_bloque.setdefault(clave, {}).setdefault(fecha, {})[campo] = valor

    for clave, muestras in muestras_bloque.items():
        if clave not in acumulados:
            acumulados[clave] = _nuevo_acumulado()
        for fecha in sorted(muestras):
            _procesar_muestra(acumulados[clave], fecha, muestras[fecha])
    # Todas las referencias al bloque se liberan al retornar, antes de consultar otro.


def calcular_saturacion_actual() -> dict[str, Any]:
    """Evalúa cuatro días cronológicamente mediante 192 bloques secuenciales."""
    logger.info("HFC: iniciando actualización")
    fin = datetime.now(timezone.utc)
    inicio = fin - timedelta(days=VENTANA_DIAS)
    acumulados: dict[tuple[str, str, str], dict[str, Any]] = {}

    for indice in range(TOTAL_BLOQUES):
        bloque_inicio = inicio + timedelta(minutes=indice * CHUNK_MINUTOS)
        bloque_fin = min(bloque_inicio + timedelta(minutes=CHUNK_MINUTOS), fin)
        _procesar_bloque(
            iterar_flux_temp(obtener_muestras_flux(bloque_inicio, bloque_fin), fuente="cmts"),
            acumulados,
        )
        bloque_actual = indice + 1
        porcentaje = round(bloque_actual / TOTAL_BLOQUES * 100.0, 2)
        guardar_estado({
            **leer_estado(),
            "estado": "procesando",
            "fase": "consultando_influx",
            "bloque_actual": bloque_actual,
            "bloques_totales": TOTAL_BLOQUES,
            "porcentaje": porcentaje,
            "ultimo_bloque_en": datetime.now().astimezone().isoformat(timespec="seconds"),
            "error": None,
        })
        logger.info("HFC: bloque %d/%d completado (%.2f%%)", bloque_actual, TOTAL_BLOQUES, porcentaje)
        if bloque_actual < TOTAL_BLOQUES:
            time.sleep(0.5)

    guardar_estado({
        **leer_estado(),
        "estado": "procesando",
        "fase": "analizando_resultados",
        "porcentaje": 100.0,
        "bloque_actual": TOTAL_BLOQUES,
        "bloques_totales": TOTAL_BLOQUES,
        "error": None,
    })
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
    logger.info("HFC: puertos confirmados=%d", sum(len(grupo["puertos"]) for grupo in datos))
    return {"datos": datos}


def actualizar_saturacion() -> dict[str, Any]:
    """Reemplaza el cache solamente después de finalizar correctamente."""
    resultado = calcular_saturacion_actual()
    cache = {
        "generado_en": datetime.now().astimezone().isoformat(timespec="seconds"),
        "ventana": "4d",
        "datos": resultado["datos"],
    }
    guardar_saturacion(cache)
    logger.info("HFC: cache actualizado")
    return cache
