"""Calculo y persistencia de la saturacion actual CMTS."""

from collections import defaultdict
from contextlib import closing
from datetime import datetime, timedelta, timezone
import logging
import math
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import time
from typing import Any

from microservicios.cmts.saturacion.cache import guardar_saturacion
from microservicios.cmts.saturacion.queries import obtener_bw_flux, obtener_muestras_flux
from microservicios.influx import consultar_flux_temp

MIN_PUNTOS_SATURACION = 100
UMBRAL_UTILIZACION = 90.0
UMBRAL_CAPACIDAD_DEGRADADA = 80.0
VENTANA_DIAS = 4
CHUNK_HORAS = 4
logger = logging.getLogger(__name__)


def _valor_numerico(fila: dict[str, Any]) -> float | None:
    try:
        valor = float(fila["_value"])
    except (KeyError, TypeError, ValueError):
        return None
    return valor if math.isfinite(valor) else None


def calcular_saturacion_actual() -> dict[str, Any]:
    """Procesa 24 bloques y conserva las muestras de uso solo en disco."""
    logger.info("HFC: iniciando actualización")
    fin = datetime.now(timezone.utc)
    inicio = fin - timedelta(days=VENTANA_DIAS)
    bw_por_puerto: dict[tuple[str, str], float] = {}
    for fila in consultar_flux_temp(obtener_bw_flux(), fuente="cmts"):
        valor = _valor_numerico(fila)
        if fila.get("cmts") and fila.get("descripcion") and valor is not None and valor > 0:
            bw_por_puerto[(str(fila["cmts"]), str(fila["descripcion"]))] = valor
    logger.info("HFC: BW puertos=%d", len(bw_por_puerto))
    if not bw_por_puerto:
        raise RuntimeError("No se obtuvieron datos BW CMTS")

    portadoras_por_puerto: dict[tuple[str, str], tuple[datetime, float, float]] = {}
    acumulados: dict[tuple[str, str], dict[str, float | int]] = {}
    cantidad_muestras_utilizacion = 0
    total_bloques = VENTANA_DIAS * 24 // CHUNK_HORAS

    with TemporaryDirectory(prefix="hfc_saturacion_") as temporal:
        with closing(sqlite3.connect(Path(temporal) / "muestras.sqlite3")) as base:
            base.execute("CREATE TABLE muestras (cmts TEXT, descripcion TEXT, utilizacion REAL)")
            for indice in range(total_bloques):
                bloque_inicio = inicio + timedelta(hours=indice * CHUNK_HORAS)
                bloque_fin = min(bloque_inicio + timedelta(hours=CHUNK_HORAS), fin)
                filas = consultar_flux_temp(obtener_muestras_flux(bloque_inicio, bloque_fin), fuente="cmts")
                for fila in filas:
                    cmts, descripcion = fila.get("cmts"), fila.get("descripcion")
                    valor = _valor_numerico(fila)
                    if not cmts or not descripcion or valor is None:
                        continue
                    clave = (str(cmts), str(descripcion))
                    if fila.get("_field") == "portadoras":
                        fecha = fila.get("_time")
                        if not isinstance(fecha, datetime) or valor <= 0:
                            continue
                        anterior = portadoras_por_puerto.get(clave)
                        if anterior is None:
                            portadoras_por_puerto[clave] = (fecha, valor, valor)
                        else:
                            fecha_actual, actual, normal = anterior
                            if fecha > fecha_actual:
                                fecha_actual, actual = fecha, valor
                            portadoras_por_puerto[clave] = (fecha_actual, actual, max(normal, valor))
                    elif fila.get("_field") == "utilizacion":
                        base.execute("INSERT INTO muestras VALUES (?, ?, ?)", (*clave, valor))
                        cantidad_muestras_utilizacion += 1
                del filas
                base.commit()
                logger.info("HFC: bloque %d/%d completado", indice + 1, total_bloques)
                if indice + 1 < total_bloques:
                    time.sleep(0.5)

            logger.info("HFC: portadoras puertos=%d", len(portadoras_por_puerto))
            logger.info("HFC: muestras utilizacion=%d", cantidad_muestras_utilizacion)
            if not portadoras_por_puerto:
                raise RuntimeError("No se obtuvieron datos de portadoras CMTS")
            if cantidad_muestras_utilizacion == 0:
                raise RuntimeError("No se obtuvieron muestras de utilización CMTS")

            capacidades: dict[tuple[str, str], tuple[float, float, bool]] = {}
            for clave, (_, actual, normal) in portadoras_por_puerto.items():
                bw_actual = bw_por_puerto.get(clave)
                if bw_actual is None:
                    continue
                porcentaje_capacidad = actual / normal * 100.0
                degradado = porcentaje_capacidad <= UMBRAL_CAPACIDAD_DEGRADADA
                umbral = UMBRAL_UTILIZACION - (100.0 - porcentaje_capacidad) if degradado else UMBRAL_UTILIZACION
                bw_normal = bw_actual * normal / actual
                capacidades[clave] = (bw_normal, umbral, degradado)

            for cmts, descripcion, utilizacion in base.execute(
                "SELECT cmts, descripcion, utilizacion FROM muestras"
            ):
                clave = (cmts, descripcion)
                capacidad = capacidades.get(clave)
                if capacidad is None:
                    continue
                bw_normal, umbral, _ = capacidad
                porcentaje = max(0.0, min(100.0, utilizacion / bw_normal * 100.0))
                acumulado = acumulados.setdefault(clave, {
                    "muestras_analizadas": 0, "puntos_sobre_90": 0, "suma_sobre_90": 0.0,
                })
                acumulado["muestras_analizadas"] += 1
                if porcentaje >= umbral:
                    acumulado["puntos_sobre_90"] += 1
                    acumulado["suma_sobre_90"] += porcentaje

    resultado: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (cmts, descripcion), acumulado in acumulados.items():
        _, _, degradado = capacidades[(cmts, descripcion)]
        puntos_sobre_90 = int(acumulado["puntos_sobre_90"])
        if puntos_sobre_90 < MIN_PUNTOS_SATURACION:
            continue
        porcentaje = acumulado["suma_sobre_90"] / puntos_sobre_90
        resultado[cmts].append({
            "puerto": descripcion, "valor": round(porcentaje, 2),
            "bw": bw_por_puerto[(cmts, descripcion)],
            "estado": "Saturación por degradación" if degradado else "Saturación",
            "tipo": "degradacion" if degradado else "uso",
            "puntos_sobre_90": puntos_sobre_90,
            "muestras_analizadas": int(acumulado["muestras_analizadas"]),
            "ruido": None,
        })

    def criticidad(item: dict[str, Any]) -> tuple[int, float]:
        return int(item["puntos_sobre_90"]), float(item["valor"])

    datos = [
        {"cmts": cmts, "puertos": sorted(puertos, key=criticidad, reverse=True)}
        for cmts, puertos in resultado.items()
    ]
    datos.sort(key=lambda grupo: criticidad(grupo["puertos"][0]), reverse=True)
    logger.info("HFC: puertos evaluados=%d", len(acumulados))
    logger.info("HFC: puertos saturados=%d", sum(len(grupo["puertos"]) for grupo in datos))
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
