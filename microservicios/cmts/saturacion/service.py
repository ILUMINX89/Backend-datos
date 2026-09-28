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
from microservicios.cmts.saturacion.queries import obtener_muestras_flux
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

    if not math.isfinite(valor):
        return None

    return valor


def calcular_saturacion_actual() -> dict[str, Any]:
    """
    Procesa los 4 dias en 24 bloques de 4 horas.

    BW:
        Se conserva en memoria solamente:
        - ultimo valor
        - maximo valor de los 4 dias

    Utilizacion:
        Se guarda temporalmente en SQLite para no mantener
        todas las muestras en RAM.
    """

    logger.info("HFC: iniciando actualización")

    fin = datetime.now(timezone.utc)
    inicio = fin - timedelta(days=VENTANA_DIAS)

    total_bloques = VENTANA_DIAS * 24 // CHUNK_HORAS

    # clave:
    # (cmts, descripcion)
    #
    # valor:
    # (
    #   fecha_ultimo_bw,
    #   bw_actual,
    #   bw_normal/maximo
    # )
    bw_por_puerto: dict[
        tuple[str, str],
        tuple[datetime, float, float],
    ] = {}

    acumulados: dict[
        tuple[str, str],
        dict[str, float | int],
    ] = {}

    cantidad_muestras_utilizacion = 0

    capacidades: dict[
        tuple[str, str],
        tuple[float, float, bool],
    ] = {}

    with TemporaryDirectory(prefix="hfc_saturacion_") as temporal:

        ruta_db = Path(temporal) / "muestras.sqlite3"

        with closing(sqlite3.connect(ruta_db)) as base:

            base.execute("""
                CREATE TABLE muestras (
                    cmts TEXT,
                    descripcion TEXT,
                    utilizacion REAL
                )
                """)

            # ==========================================
            # CONSULTAR 24 BLOQUES
            # ==========================================

            for indice in range(total_bloques):

                bloque_inicio = inicio + timedelta(hours=indice * CHUNK_HORAS)

                bloque_fin = min(
                    bloque_inicio + timedelta(hours=CHUNK_HORAS),
                    fin,
                )

                filas = consultar_flux_temp(
                    obtener_muestras_flux(
                        bloque_inicio,
                        bloque_fin,
                    ),
                    fuente="cmts",
                )

                # ======================================
                # PROCESAR BLOQUE INMEDIATAMENTE
                # ======================================

                for fila in filas:

                    cmts = fila.get("cmts")
                    descripcion = fila.get("descripcion")
                    campo = fila.get("_field")

                    valor = _valor_numerico(fila)

                    if not cmts or not descripcion or valor is None:
                        continue

                    clave = (
                        str(cmts),
                        str(descripcion),
                    )

                    # ==================================
                    # BW
                    # ==================================

                    if campo == "bw":

                        fecha = fila.get("_time")

                        if not isinstance(fecha, datetime) or valor <= 0:
                            continue

                        anterior = bw_por_puerto.get(clave)

                        if anterior is None:

                            bw_por_puerto[clave] = (
                                fecha,
                                valor,
                                valor,
                            )

                        else:

                            (
                                fecha_actual,
                                bw_actual,
                                bw_normal,
                            ) = anterior

                            # ultimo BW
                            if fecha > fecha_actual:
                                fecha_actual = fecha
                                bw_actual = valor

                            # maximo BW de los 4 dias
                            bw_normal = max(
                                bw_normal,
                                valor,
                            )

                            bw_por_puerto[clave] = (
                                fecha_actual,
                                bw_actual,
                                bw_normal,
                            )

                    # ==================================
                    # UTILIZACION
                    # ==================================

                    elif campo == "utilizacion":

                        base.execute(
                            """
                            INSERT INTO muestras
                            VALUES (?, ?, ?)
                            """,
                            (
                                clave[0],
                                clave[1],
                                valor,
                            ),
                        )

                        cantidad_muestras_utilizacion += 1

                # Liberar bloque antes de pedir el siguiente
                del filas

                base.commit()

                logger.info(
                    "HFC: bloque %d/%d completado",
                    indice + 1,
                    total_bloques,
                )

                if indice + 1 < total_bloques:
                    time.sleep(0.5)

            # ==========================================
            # VALIDAR FUENTES
            # ==========================================

            logger.info(
                "HFC: BW puertos=%d",
                len(bw_por_puerto),
            )

            logger.info(
                "HFC: muestras utilizacion=%d",
                cantidad_muestras_utilizacion,
            )

            if not bw_por_puerto:
                raise RuntimeError("No se obtuvieron datos BW CMTS")

            if cantidad_muestras_utilizacion == 0:
                raise RuntimeError("No se obtuvieron muestras de utilización CMTS")

            # ==========================================
            # CALCULAR UMBRAL POR PUERTO
            # ==========================================

            for clave, (
                _,
                bw_actual,
                bw_normal,
            ) in bw_por_puerto.items():

                if bw_actual <= 0 or bw_normal <= 0:
                    continue

                porcentaje_capacidad = bw_actual / bw_normal * 100.0

                # Si queda al 80% o menos:
                # se considera degradado.
                degradado = porcentaje_capacidad <= UMBRAL_CAPACIDAD_DEGRADADA

                if degradado:

                    degradacion = 100.0 - porcentaje_capacidad

                    umbral = UMBRAL_UTILIZACION - degradacion

                    # Protección por valores extremos
                    umbral = max(
                        0.0,
                        min(
                            UMBRAL_UTILIZACION,
                            umbral,
                        ),
                    )

                else:
                    umbral = UMBRAL_UTILIZACION

                capacidades[clave] = (
                    bw_actual,
                    umbral,
                    degradado,
                )

            logger.info(
                "HFC: puertos con capacidad=%d",
                len(capacidades),
            )

            # ==========================================
            # PROCESAR UTILIZACION DESDE DISCO
            # ==========================================

            cursor = base.execute("""
                SELECT
                    cmts,
                    descripcion,
                    utilizacion
                FROM muestras
                """)

            for (
                cmts,
                descripcion,
                utilizacion,
            ) in cursor:

                clave = (
                    cmts,
                    descripcion,
                )

                capacidad = capacidades.get(clave)

                if capacidad is None:
                    continue

                (
                    bw_actual,
                    umbral,
                    _,
                ) = capacidad

                # IMPORTANTE:
                # Esta es la formula que funcionaba antes.
                porcentaje = utilizacion / bw_actual * 100.0

                porcentaje = max(
                    0.0,
                    min(
                        100.0,
                        porcentaje,
                    ),
                )

                acumulado = acumulados.setdefault(
                    clave,
                    {
                        "muestras_analizadas": 0,
                        "puntos_sobre_90": 0,
                        "suma_sobre_90": 0.0,
                    },
                )

                acumulado["muestras_analizadas"] += 1

                if porcentaje >= umbral:

                    acumulado["puntos_sobre_90"] += 1

                    acumulado["suma_sobre_90"] += porcentaje

    # ==============================================
    # GENERAR RESULTADO
    # ==============================================

    resultado: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    for (
        cmts,
        descripcion,
    ), acumulado in acumulados.items():

        capacidad = capacidades.get(
            (
                cmts,
                descripcion,
            )
        )

        if capacidad is None:
            continue

        (
            bw_actual,
            _,
            degradado,
        ) = capacidad

        puntos = int(acumulado["puntos_sobre_90"])

        # Necesita mínimo 100 puntos
        if puntos < MIN_PUNTOS_SATURACION:
            continue

        porcentaje = acumulado["suma_sobre_90"] / puntos

        porcentaje = max(
            0.0,
            min(
                100.0,
                porcentaje,
            ),
        )

        resultado[cmts].append(
            {
                "puerto": descripcion,
                "valor": round(
                    porcentaje,
                    2,
                ),
                "bw": bw_actual,
                "estado": ("Saturación por degradación" if degradado else "Saturación"),
                "tipo": ("degradacion" if degradado else "uso"),
                # Se conserva el nombre por
                # compatibilidad con frontend/API.
                "puntos_sobre_90": puntos,
                "muestras_analizadas": int(acumulado["muestras_analizadas"]),
                "ruido": None,
            }
        )

    # ==============================================
    # ORDENAR POR CRITICIDAD
    # ==============================================

    def criticidad(
        item: dict[str, Any],
    ) -> tuple[int, float]:

        return (
            int(item["puntos_sobre_90"]),
            float(item["valor"]),
        )

    datos = [
        {
            "cmts": cmts,
            "puertos": sorted(
                puertos,
                key=criticidad,
                reverse=True,
            ),
        }
        for cmts, puertos in resultado.items()
    ]

    datos.sort(
        key=lambda grupo: criticidad(grupo["puertos"][0]),
        reverse=True,
    )

    logger.info(
        "HFC: puertos evaluados=%d",
        len(acumulados),
    )

    logger.info(
        "HFC: puertos saturados=%d",
        sum(len(grupo["puertos"]) for grupo in datos),
    )

    return {"datos": datos}


def actualizar_saturacion() -> dict[str, Any]:
    """
    Reemplaza el cache solamente después
    de finalizar correctamente.
    """

    resultado = calcular_saturacion_actual()

    cache = {
        "generado_en": (datetime.now().astimezone().isoformat(timespec="seconds")),
        "ventana": "4d",
        "datos": resultado["datos"],
    }

    guardar_saturacion(cache)

    logger.info("HFC: cache actualizado")

    return cache
