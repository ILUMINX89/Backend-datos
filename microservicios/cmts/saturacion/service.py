"""Logica de negocio para saturacion actual CMTS."""

from collections import defaultdict
from typing import Any

from microservicios.cmts.saturacion.queries import (
    obtener_bw_flux,
    obtener_snr_flux,
    obtener_utilizacion_flux,
)
from microservicios.influx import consultar_flux_temp

MUESTRAS_CONFIRMACION = 3
UMBRAL_UTILIZACION = 80.0
# Regla aislada para ajuste operacional: el bucket no define un umbral verificable.
UMBRAL_SNR_DEGRADADO_DB = 30.0


def _agrupar(filas: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    resultado: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for fila in filas:
        cmts = fila.get("cmts")
        descripcion = fila.get("descripcion")
        if not cmts or not descripcion or fila.get("_value") is None:
            continue
        resultado[(str(cmts), str(descripcion))].append(fila)
    for muestras in resultado.values():
        muestras.sort(key=lambda fila: fila.get("_time"), reverse=True)
    return dict(resultado)


def obtener_saturacion_actual() -> dict[str, Any]:
    muestras_bw = _agrupar(consultar_flux_temp(obtener_bw_flux(), fuente="cmts"))
    muestras_utilizacion = _agrupar(
        consultar_flux_temp(obtener_utilizacion_flux(), fuente="cmts")
    )
    muestras_snr = _agrupar(consultar_flux_temp(obtener_snr_flux(), fuente="cmts"))
    resultado: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for (cmts, descripcion), filas_bw in muestras_bw.items():
        clave = (cmts, descripcion)
        filas_utilizacion = muestras_utilizacion.get(clave, [])
        if not filas_bw or not filas_utilizacion:
            continue
        try:
            bw_origen = filas_bw[0]["_value"]
            bw = float(bw_origen)
            utilizacion_origen = filas_utilizacion[0]["_value"]
            utilizacion = float(utilizacion_origen)
        except (TypeError, ValueError):
            continue
        if bw <= 0:
            continue

        porcentaje = (utilizacion / bw) * 100.0
        porcentajes: list[float] = []
        for fila in filas_utilizacion[:MUESTRAS_CONFIRMACION]:
            try:
                porcentajes.append((float(fila["_value"]) / bw) * 100.0)
            except (KeyError, TypeError, ValueError):
                break

        filas_ruido = muestras_snr.get(clave, [])[:MUESTRAS_CONFIRMACION]
        valores_ruido: list[float] = []
        for fila in filas_ruido:
            try:
                valor_ruido = float(fila["_value"])
            except (KeyError, TypeError, ValueError):
                break
            if valor_ruido <= 0:
                break
            valores_ruido.append(valor_ruido)

        uso_confirmado = (
            len(porcentajes) == MUESTRAS_CONFIRMACION
            and all(valor > UMBRAL_UTILIZACION for valor in porcentajes)
        )
        degradacion_confirmada = (
            len(valores_ruido) == MUESTRAS_CONFIRMACION
            and all(valor < UMBRAL_SNR_DEGRADADO_DB for valor in valores_ruido)
        )
        if not uso_confirmado and not degradacion_confirmada:
            continue

        tipo = "degradacion" if degradacion_confirmada else "uso"
        estado = "Saturación por degradación" if degradacion_confirmada else "Saturación"
        resultado[cmts].append(
            {
                "puerto": descripcion,
                "valor": round(porcentaje, 2),
                "bw": bw_origen,
                "utilizacion": utilizacion_origen,
                "estado": estado,
                "tipo": tipo,
                "muestras_confirmacion": MUESTRAS_CONFIRMACION,
                "ruido": valores_ruido[0] if valores_ruido else None,
            }
        )

    datos: list[dict[str, Any]] = []
    for cmts in resultado:
        puertos = sorted(resultado[cmts], key=lambda item: item["valor"], reverse=True)
        datos.append({"cmts": cmts, "puertos": puertos})
    datos.sort(key=lambda grupo: grupo["puertos"][0]["valor"], reverse=True)
    return {"datos": datos}
