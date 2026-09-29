"""Normalización de lecturas actuales de pérdida y latencia OLT."""

from math import isfinite
from typing import Any

from microservicios.mysql import consultar_mysql
from microservicios.olt.perdida_latencia.queries import CONSULTA_PERDIDA_LATENCIA_ACTUAL


def _numero_finito(valor: Any) -> float | None:
    try:
        numero = float(valor)
    except (TypeError, ValueError, OverflowError):
        return None
    return numero if isfinite(numero) else None


def obtener_perdida_latencia_actual() -> dict[str, Any]:
    filas = consultar_mysql(CONSULTA_PERDIDA_LATENCIA_ACTUAL)
    eventos = []

    for fila in filas:
        equipo = str(fila.get("EQUIPO") or "").strip()
        if not equipo:
            continue

        perdida = _numero_finito(fila.get("PACKET_LOSS"))
        latencia = _numero_finito(fila.get("LATENCIA_AVG"))
        perdida = perdida if perdida is not None and perdida > 10 else None
        latencia = latencia if latencia is not None and latencia > 50 else None

        if perdida is not None:
            evento = {
                "equipo": equipo,
                "valor": round(perdida, 2),
                "unidad": "%",
                "estado": "Pérdida",
                "nivel": "rojo" if perdida == 100 else "neutral",
            }
            if latencia is not None:
                evento.update({
                    "valor_secundario": round(latencia, 2),
                    "unidad_secundaria": "ms",
                    "estado": "Pérdida + Latencia",
                })
            eventos.append(evento)
        elif latencia is not None:
            eventos.append({
                "equipo": equipo,
                "valor": round(latencia, 2),
                "unidad": "ms",
                "estado": "Latencia",
                "nivel": "neutral",
            })

    return {
        "consulta": "perdida_latencia_actual",
        "cantidad": len(eventos),
        "datos": eventos,
    }
