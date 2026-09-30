"""Calculo y persistencia de la saturacion actual CMTS."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import logging
import math
import time
from typing import Any

from microservicios.cmts.saturacion.cache import guardar_saturacion
from microservicios.cmts.saturacion.queries import obtener_muestras_flux
from microservicios.influx import consultar_flux_temp

UMBRAL_UTILIZACION = 80.0
UMBRAL_SNR_DEGRADADO_DB = 30.0
MUESTRAS_CONFIRMACION_SNR = 60
MBPS_POR_PORTADORA = 30
VENTANA_DIAS = 4
CHUNK_HORAS = 4

logger = logging.getLogger(__name__)


def _valor_numerico(fila: dict[str, Any]) -> float | None:
    try:
        valor = float(fila["_value"])
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
    return valor if math.isfinite(valor) else None


def calcular_saturacion_actual() -> dict[str, Any]:
    """Evalua utilizacion y SNR por puerto en bloques de cuatro horas."""
    logger.info("HFC: iniciando actualización")
    fin = datetime.now(timezone.utc)
    inicio = fin - timedelta(days=VENTANA_DIAS)
    total_bloques = VENTANA_DIAS * 24 // CHUNK_HORAS

    acumulados: dict[tuple[str, str, str], dict[str, Any]] = {}

    for indice in range(total_bloques):
        bloque_inicio = inicio + timedelta(hours=indice * CHUNK_HORAS)
        bloque_fin = min(bloque_inicio + timedelta(hours=CHUNK_HORAS), fin)
        filas = consultar_flux_temp(
            obtener_muestras_flux(bloque_inicio, bloque_fin), fuente="cmts"
        )

        # Sólo se retienen las lecturas del bloque actual.
        muestras: dict[tuple[str, str, str, datetime], dict[str, float]] = {}
        for fila in filas:
            cmts = fila.get("cmts")
            puerto = fila.get("puerto")
            descripcion = fila.get("descripcion")
            fecha = fila.get("_time")
            campo = fila.get("_field")
            valor = _valor_numerico(fila)
            if (
                not cmts or not puerto or not descripcion
                or not isinstance(fecha, datetime)
                or campo not in ("bw", "utilizacion", "snr", "portadoras")
                or valor is None
            ):
                continue

            clave = (str(cmts), str(puerto), str(descripcion))
            acumulado = acumulados.setdefault(clave, {
                "muestras_analizadas": 0,
                "puntos_sobre_80": 0,
                "suma_sobre_80": 0.0,
                "ultimo_bw": None,
                "ultima_fecha_bw": None,
                "portadoras": None,
                "ultima_fecha_portadoras": None,
                "muestras_snr": 0,
                "muestras_snr_degradadas": 0,
                "suma_snr_degradado": 0.0,
            })
            if campo == "bw":
                if valor <= 0:
                    continue
                if acumulado["ultima_fecha_bw"] is None or fecha > acumulado["ultima_fecha_bw"]:
                    acumulado["ultima_fecha_bw"] = fecha
                    acumulado["ultimo_bw"] = valor
            elif campo == "portadoras":
                if valor <= 0 or not valor.is_integer():
                    continue
                if acumulado["ultima_fecha_portadoras"] is None or fecha > acumulado["ultima_fecha_portadoras"]:
                    acumulado["ultima_fecha_portadoras"] = fecha
                    acumulado["portadoras"] = int(valor)

            muestras.setdefault((*clave, fecha), {})[campo] = valor

        del filas
        for (cmts, puerto, descripcion, _fecha), muestra in muestras.items():
            utilizacion = muestra.get("utilizacion")
            acumulado = acumulados[(cmts, puerto, descripcion)]
            if utilizacion is not None:
                acumulado["muestras_analizadas"] += 1
                if utilizacion > UMBRAL_UTILIZACION:
                    acumulado["puntos_sobre_80"] += 1
                    acumulado["suma_sobre_80"] += max(0.0, min(100.0, utilizacion))
            snr = muestra.get("snr")
            if snr is not None:
                acumulado["muestras_snr"] += 1
                if snr < UMBRAL_SNR_DEGRADADO_DB:
                    acumulado["muestras_snr_degradadas"] += 1
                    acumulado["suma_snr_degradado"] += snr
        del muestras

        logger.info("HFC: bloque %d/%d completado", indice + 1, total_bloques)
        if indice + 1 < total_bloques:
            time.sleep(0.5)

    resultado: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (cmts, puerto, descripcion), acumulado in acumulados.items():
        puntos = int(acumulado["puntos_sobre_80"])
        degradados = acumulado["muestras_snr_degradadas"]
        degradado = degradados >= MUESTRAS_CONFIRMACION_SNR
        if not puntos and not degradado:
            continue
        porcentaje = acumulado["suma_sobre_80"] / puntos if puntos else 0.0
        portadoras = acumulado["portadoras"]
        resultado[cmts].append({
            "puerto": descripcion,
            "puerto_fisico": puerto,
            "valor": round(porcentaje, 2),
            "bw": portadoras * MBPS_POR_PORTADORA if portadoras is not None else acumulado["ultimo_bw"],
            "estado": "Saturación / Degradación" if puntos and degradado else "Degradación" if degradado else "Saturación",
            "tipo": "degradacion" if degradado else "uso",
            "puntos_sobre_80": puntos,
            "muestras_analizadas": int(acumulado["muestras_analizadas"]),
            "ruido": round(acumulado["suma_snr_degradado"] / degradados, 2) if degradado else None,
        })

    def criticidad(item: dict[str, Any]) -> tuple[int, float]:
        return (int(item["puntos_sobre_80"]), float(item["valor"]))

    datos = [
        {"cmts": cmts, "puertos": sorted(puertos, key=criticidad, reverse=True)}
        for cmts, puertos in resultado.items()
    ]
    datos.sort(key=lambda grupo: criticidad(grupo["puertos"][0]), reverse=True)
    logger.info("HFC: puertos evaluados=%d", len(acumulados))
    logger.info("HFC: puertos saturados=%d", sum(len(grupo["puertos"]) for grupo in datos))
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
