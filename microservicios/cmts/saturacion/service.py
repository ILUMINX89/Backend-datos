"""Logica de negocio para saturacion actual CMTS."""

from collections import defaultdict
from typing import Any

from microservicios.cmts.saturacion.queries import obtener_bw_flux, obtener_utilizacion_flux
from microservicios.influx import consultar_flux_temp


def _indexar(filas: list[dict[str, Any]]) -> dict[tuple[str, str], Any]:
    resultado: dict[tuple[str, str], Any] = {}
    for fila in filas:
        cmts = fila.get("cmts")
        descripcion = fila.get("descripcion")
        if not cmts or not descripcion or fila.get("_value") is None:
            continue
        resultado[(str(cmts), str(descripcion))] = fila["_value"]
    return resultado


def obtener_saturacion_actual() -> dict[str, Any]:
    datos_bw = _indexar(consultar_flux_temp(obtener_bw_flux(), fuente="cmts"))
    datos_utilizacion = _indexar(
        consultar_flux_temp(obtener_utilizacion_flux(), fuente="cmts")
    )
    resultado: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for (cmts, descripcion), bw_origen in datos_bw.items():
        if (cmts, descripcion) not in datos_utilizacion:
            continue
        try:
            bw = float(bw_origen)
            utilizacion_origen = datos_utilizacion[(cmts, descripcion)]
            utilizacion = float(utilizacion_origen)
        except (TypeError, ValueError):
            continue
        if bw <= 0:
            continue

        porcentaje = (utilizacion / bw) * 100.0
        if porcentaje <= 80.0:
            continue
        resultado[cmts].append(
            {
                "puerto": descripcion,
                "valor": round(porcentaje, 2),
                "bw": bw_origen,
                "utilizacion": utilizacion_origen,
            }
        )

    datos = []
    for cmts in sorted(resultado):
        puertos = sorted(resultado[cmts], key=lambda item: item["valor"], reverse=True)
        datos.append({"cmts": cmts, "puertos": puertos})
    return {"datos": datos}
