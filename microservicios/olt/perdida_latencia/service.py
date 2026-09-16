"""Normalización de lecturas actuales e históricas de ping OLT."""

from datetime import date, datetime
from math import isfinite
from typing import Any

from microservicios.influx import consultar_flux_temp
from microservicios.olt.perdida_latencia.queries import (
    EQUIPO_VALIDO,
    obtener_latencia_actual_flux,
    obtener_latencia_equipo_flux,
)


def _numero_finito(valor: Any) -> float | None:
    try:
        numero = float(valor)
    except (TypeError, ValueError, OverflowError):
        return None
    return numero if isfinite(numero) else None


def _timestamp(valor: Any) -> str | None:
    if isinstance(valor, (date, datetime)):
        return valor.isoformat().replace("+00:00", "Z")
    if isinstance(valor, str) and valor.strip():
        return valor.strip()
    return None


def obtener_perdida_latencia_actual() -> dict[str, Any]:
    filas = consultar_flux_temp(
        obtener_latencia_actual_flux(),
        fuente="red",
    )
    equipos: dict[str, dict[str, Any]] = {}

    for fila in filas:
        equipo = str(fila.get("equipo") or "").strip()
        if EQUIPO_VALIDO.fullmatch(equipo) is None:
            continue

        campo = fila.get("_field")
        if campo not in {"latency", "packet_loss"}:
            continue

        valor = _numero_finito(fila.get("_value"))
        if valor is None:
            continue

        registro = equipos.setdefault(
            equipo,
            {
                "equipo": equipo,
                "perdida": None,
                "latencia": None,
                "unidad_latencia": None,
                "estado": "Latencia registrada",
                "nivel": "neutral",
                "ultima_muestra": None,
                "tiempo": None,
            },
        )

        if campo == "latency":
            registro["latencia"] = round(valor, 2)
            registro["ultima_muestra"] = _timestamp(fila.get("_time"))
        else:
            registro["perdida"] = round(valor, 2)

    datos = [fila for fila in equipos.values() if fila["latencia"] is not None]
    datos.sort(key=lambda fila: fila["equipo"])

    return {
        "consulta": "perdida_latencia_actual",
        "periodo": "ultimos_10_minutos",
        "cantidad": len(datos),
        "datos": datos,
    }


def obtener_latencia_equipo(
    equipo: str,
    periodo: str = "-30d",
) -> dict[str, Any]:
    filas = consultar_flux_temp(
        obtener_latencia_equipo_flux(equipo, periodo),
        fuente="red",
    )
    datos = []

    for fila in filas:
        latencia = _numero_finito(fila.get("_value"))
        muestra = _timestamp(fila.get("_time"))
        if latencia is None or muestra is None:
            continue
        datos.append({"latencia": round(latencia, 2), "ultima_muestra": muestra})

    return {
        "consulta": "latencia_equipo",
        "equipo": equipo.strip(),
        "periodo": periodo,
        "unidad_latencia": None,
        "cantidad": len(datos),
        "datos": datos,
    }
