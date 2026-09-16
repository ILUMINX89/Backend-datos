"""Lecturas de temperatura máxima actual por equipo OLT."""

from math import isfinite
from typing import Any

from microservicios.influx import consultar_flux_temp
from microservicios.olt.temperatura.queries import (
    obtener_temperatura_actual_flux,
)

UMBRAL_AMARILLO = 70.0
UMBRAL_NARANJA = 80.0
UMBRAL_ROJO = 90.0


def clasificar_temperatura(
    temperatura: float,
) -> tuple[str, str]:
    if temperatura >= UMBRAL_ROJO:
        return "Crítico", "rojo"

    if temperatura >= UMBRAL_NARANJA:
        return "Alta", "naranja"

    return "Advertencia", "amarillo"


def obtener_temperatura_actual() -> dict[str, Any]:
    maximas_por_olt: dict[str, float] = {}

    filas = consultar_flux_temp(obtener_temperatura_actual_flux())

    for fila in filas:
        olt = str(fila.get("OLT") or "").strip()

        tarjeta = str(fila.get("TARJETA") or "").strip()

        if not olt or not tarjeta:
            continue

        try:
            temperatura = float(fila.get("TEMPERATURA"))
        except (
            TypeError,
            ValueError,
            OverflowError,
        ):
            continue

        if not isfinite(temperatura):
            continue

        # Valor inválido enviado por la fuente.
        if temperatura == 2147483647:
            continue

        maximas_por_olt[olt] = max(maximas_por_olt.get(olt, temperatura), temperatura)

    datos = []
    for olt, temperatura in maximas_por_olt.items():
        # Temperaturas normales no se muestran.
        if temperatura < UMBRAL_AMARILLO:
            continue

        estado, nivel = clasificar_temperatura(temperatura)
        datos.append(
            {
                "olt": olt,
                "temperatura": round(temperatura, 2),
                "estado": estado,
                "nivel": nivel,
            }
        )

    # Mostrar primero las temperaturas más críticas.
    datos.sort(
        key=lambda fila: (
            -fila["temperatura"],
            fila["olt"],
        )
    )

    return {
        "consulta": "temperatura_actual_olt",
        "periodo": "ultimos_10_minutos",
        "criterio": "temperatura_mayor_o_igual_70",
        "umbrales": {
            "amarillo": UMBRAL_AMARILLO,
            "naranja": UMBRAL_NARANJA,
            "rojo": UMBRAL_ROJO,
        },
        "cantidad": len(datos),
        "datos": datos,
    }
