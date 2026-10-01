"""Normalización de recursos ZTE con baja disponibilidad."""

from datetime import date, datetime
from math import isfinite
from typing import Any

from microservicios.olt.recursos_zte.queries import obtener_licencias_bajas_mysql

UMBRAL_DISPONIBLE_PCT = 15.0


def _numero_finito(valor: Any) -> float | None:
    try:
        numero = float(valor)
    except (TypeError, ValueError, OverflowError):
        return None
    return numero if isfinite(numero) else None


def _fecha_serializable(valor: Any) -> str | None:
    if isinstance(valor, datetime):
        return valor.isoformat(sep=" ")
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, str) and valor.strip():
        return valor.strip()
    return None


def obtener_licencias_bajas() -> dict[str, Any]:
    """Devuelve alertas ZTE válidas con menos de 15 % disponible."""
    licencias: list[dict[str, Any]] = []

    for fila in obtener_licencias_bajas_mysql(UMBRAL_DISPONIBLE_PCT):
        olt = str(fila.get("olt") or "").strip()
        recurso = str(fila.get("recurso") or "").strip()
        usado = _numero_finito(fila.get("usado"))
        disponible = _numero_finito(fila.get("disponible"))
        total = _numero_finito(fila.get("total"))
        porcentaje = _numero_finito(fila.get("porcentaje_disponible"))
        actualizado_en = _fecha_serializable(fila.get("actualizado_en"))

        if (
            not olt
            or not recurso
            or usado is None
            or disponible is None
            or total is None
            or porcentaje is None
            or actualizado_en is None
            or usado < 0
            or disponible < 0
            or total <= 0
            or porcentaje < 0
            or porcentaje > 100
            or porcentaje >= UMBRAL_DISPONIBLE_PCT
        ):
            continue

        licencias.append(
            {
                "olt": olt,
                "recurso": recurso,
                "usado": int(usado) if usado.is_integer() else usado,
                "disponible": int(disponible) if disponible.is_integer() else disponible,
                "total": int(total) if total.is_integer() else total,
                "porcentaje_disponible": round(porcentaje, 4),
                "actualizado_en": actualizado_en,
            }
        )

    licencias.sort(
        key=lambda fila: (
            fila["porcentaje_disponible"],
            fila["olt"],
            fila["recurso"],
        )
    )
    return {"umbral_pct": UMBRAL_DISPONIBLE_PCT, "licencias": licencias}
