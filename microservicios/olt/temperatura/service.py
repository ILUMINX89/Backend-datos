"""Lecturas validas de temperatura actual por tarjeta OLT."""

from math import isfinite
from typing import Any

from microservicios.influx import consultar_flux_temp
from microservicios.olt.temperatura.queries import obtener_temperatura_actual_flux


def obtener_temperatura_actual() -> dict[str, Any]:
    datos = []
    for fila in consultar_flux_temp(obtener_temperatura_actual_flux()):
        olt = str(fila.get("OLT") or "")
        tarjeta = str(fila.get("TARJETA") or "")
        if not olt.strip() or not tarjeta.strip():
            continue
        try:
            temperatura = float(fila.get("TEMPERATURA"))
        except (TypeError, ValueError, OverflowError):
            continue
        if not isfinite(temperatura) or temperatura == 2147483647:
            continue
        datos.append({
            "olt": olt,
            "tarjeta": tarjeta,
            "nombre": fila.get("NOMBRE"),
            "temperatura": round(temperatura, 2),
        })

    datos.sort(key=lambda fila: (fila["olt"], fila["tarjeta"]))
    return {
        "consulta": "temperatura_actual_olt",
        "periodo": "ultimos_10_minutos",
        "cantidad": len(datos),
        "datos": datos,
    }
