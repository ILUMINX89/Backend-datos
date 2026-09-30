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
from microservicios.influx import consultar_flux_temp

UMBRAL_UTILIZACION = 80.0
UMBRAL_CAPACIDAD_DEGRADADA = 80.0
UMBRAL_SNR_DEGRADADO_DB = 30.0
MUESTRAS_CONFIRMACION_SNR = 60
MBPS_POR_PORTADORA = 30
VENTANA_DIAS = 4
CHUNK_HORAS = 1

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

        # Solo se retienen las lecturas del bloque actual.
        muestras: dict[tuple[str, str, str, datetime], dict[str, float]] = {}

        for fila in filas:
            cmts = fila.get("cmts")
            puerto = fila.get("puerto")
            descripcion = fila.get("descripcion")
            fecha = fila.get("_time")
            campo = fila.get("_field")
            valor = _valor_numerico(fila)

            if (
                not cmts
                or not puerto
                or not descripcion
                or not isinstance(fecha, datetime)
                or campo not in ("bw", "utilizacion", "snr", "portadoras")
                or valor is None
            ):
                continue

            clave = (str(cmts), str(puerto), str(descripcion))

            acumulado = acumulados.setdefault(
                clave,
                {
                    "muestras_analizadas": 0,
                    "puntos_sobre_80": 0,
                    "suma_sobre_80": 0.0,
                    "ultimo_bw": None,
                    "bw_maximo_historico": 0.0,
                    "lecturas_capacidad": {},
                    "ultima_fecha_bw": None,
                    "portadoras": None,
                    "ultima_fecha_portadoras": None,
                    "muestras_snr": 0,
                    "muestras_snr_degradadas": 0,
                    "suma_snr_degradado": 0.0,
                },
            )

            if campo == "bw":
                if valor <= 0:
                    continue

                acumulado["bw_maximo_historico"] = max(
                    acumulado["bw_maximo_historico"], valor
                )

                if (
                    acumulado["ultima_fecha_bw"] is None
                    or fecha > acumulado["ultima_fecha_bw"]
                ):
                    acumulado["ultima_fecha_bw"] = fecha
                    acumulado["ultimo_bw"] = valor

            elif campo == "portadoras":
                if valor <= 0 or not valor.is_integer():
                    continue

                if (
                    acumulado["ultima_fecha_portadoras"] is None
                    or fecha > acumulado["ultima_fecha_portadoras"]
                ):
                    acumulado["ultima_fecha_portadoras"] = fecha

                    acumulado["portadoras"] = int(valor)

            muestras.setdefault((*clave, fecha), {})[campo] = valor

        # Liberar cuanto antes las filas crudas del bloque.
        del filas

        for (cmts, puerto, descripcion, _fecha), muestra in muestras.items():

            utilizacion = muestra.get("utilizacion")
            bw_real = muestra.get("bw")

            acumulado = acumulados[(cmts, puerto, descripcion)]

            if utilizacion is not None and bw_real is not None and bw_real > 0:
                porcentaje_uso = utilizacion / bw_real * 100.0

                if not math.isfinite(porcentaje_uso):
                    continue

                acumulado["muestras_analizadas"] += 1

                saturado = porcentaje_uso > UMBRAL_UTILIZACION

                if saturado:
                    acumulado["puntos_sobre_80"] += 1

                    acumulado["suma_sobre_80"] += porcentaje_uso

                # Agrupar BW equivalentes permite
                # aplicar el máximo histórico
                # de toda la ventana sin retener
                # todas las filas.
                referencia_muestra = muestra.get("portadoras")

                conteos = acumulado["lecturas_capacidad"].setdefault(
                    (bw_real, referencia_muestra), [0, 0]
                )

                conteos[0] += 1
                conteos[1] += int(saturado)

            snr = muestra.get("snr")

            if snr is not None:
                acumulado["muestras_snr"] += 1

                if snr < UMBRAL_SNR_DEGRADADO_DB:
                    acumulado["muestras_snr_degradadas"] += 1

                    acumulado["suma_snr_degradado"] += snr

        # Liberar las muestras del bloque antes
        # de iniciar la siguiente consulta.
        del muestras

        # -------------------------------------------------
        # PROGRESO DE LA CONSULTA HFC
        # -------------------------------------------------

        bloque_actual = indice + 1

        porcentaje_progreso = round(bloque_actual / total_bloques * 100.0, 2)

        estado_actual = leer_estado()

        guardar_estado(
            {
                **estado_actual,
                "estado": "procesando",
                "fase": "consultando_influx",
                "bloque_actual": bloque_actual,
                "bloques_totales": total_bloques,
                "porcentaje": porcentaje_progreso,
                "ultimo_bloque_en": (
                    datetime.now().astimezone().isoformat(timespec="seconds")
                ),
                "error": None,
            }
        )

        logger.info(
            "HFC: bloque %d/%d completado (%.2f%%)",
            bloque_actual,
            total_bloques,
            porcentaje_progreso,
        )

        if bloque_actual < total_bloques:
            time.sleep(0.5)

    # -----------------------------------------------------
    # ANALISIS FINAL DE LOS DATOS ACUMULADOS
    # -----------------------------------------------------

    estado_actual = leer_estado()

    guardar_estado(
        {
            **estado_actual,
            "estado": "procesando",
            "fase": "analizando_resultados",
            "porcentaje": 100.0,
            "bloque_actual": total_bloques,
            "bloques_totales": total_bloques,
            "error": None,
        }
    )

    resultado: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for (cmts, puerto, descripcion), acumulado in acumulados.items():

        puntos = int(acumulado["puntos_sobre_80"])

        degradados = acumulado["muestras_snr_degradadas"]

        degradacion_snr = degradados >= MUESTRAS_CONFIRMACION_SNR

        portadoras = acumulado["portadoras"]

        capacidad_nominal = (
            portadoras * MBPS_POR_PORTADORA if portadoras is not None else None
        )

        referencia = capacidad_nominal or acumulado["bw_maximo_historico"]

        puntos_degradados = 0
        muestras_capacidad_degradada = 0

        for (bw_real, portadoras_muestra), (total, criticos) in acumulado[
            "lecturas_capacidad"
        ].items():

            capacidad = (
                portadoras_muestra * MBPS_POR_PORTADORA
                if portadoras_muestra is not None
                else referencia
            )

            if (
                capacidad > 0
                and (bw_real / capacidad * 100.0) < UMBRAL_CAPACIDAD_DEGRADADA
            ):
                muestras_capacidad_degradada += total

                puntos_degradados += criticos

        degradacion_capacidad = muestras_capacidad_degradada > 0

        if not puntos and not degradacion_snr and not degradacion_capacidad:
            continue

        porcentaje = acumulado["suma_sobre_80"] / puntos if puntos else 0.0

        if puntos:
            if puntos_degradados:
                estado = "Saturación por degradación"
                tipo = "degradacion"
            else:
                estado = "Saturación"
                tipo = "uso"
        else:
            estado = "Degradación"
            tipo = "degradacion"

        resultado[cmts].append(
            {
                "puerto": descripcion,
                "puerto_fisico": puerto,
                "valor": round(max(0.0, min(100.0, porcentaje)), 2),
                "bw": acumulado["ultimo_bw"],
                "capacidad_nominal": (capacidad_nominal),
                "bw_maximo_historico": (acumulado["bw_maximo_historico"]),
                "estado": estado,
                "tipo": tipo,
                "puntos_sobre_80": puntos,
                "muestras_analizadas": int(acumulado["muestras_analizadas"]),
                "puntos_saturacion_degradada": (puntos_degradados),
                "ruido": (
                    round(acumulado["suma_snr_degradado"] / degradados, 2)
                    if degradacion_snr
                    else None
                ),
            }
        )

    def criticidad(item: dict[str, Any]) -> tuple[int, float]:
        return (int(item["puntos_sobre_80"]), float(item["valor"]))

    datos = [
        {"cmts": cmts, "puertos": sorted(puertos, key=criticidad, reverse=True)}
        for cmts, puertos in resultado.items()
    ]

    datos.sort(key=lambda grupo: criticidad(grupo["puertos"][0]), reverse=True)

    logger.info("HFC: puertos evaluados=%d", len(acumulados))

    logger.info(
        "HFC: puertos saturados=%d", sum(len(grupo["puertos"]) for grupo in datos)
    )

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
