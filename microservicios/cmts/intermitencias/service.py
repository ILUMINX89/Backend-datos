"""Logica de negocio para intermitencias HFC."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

MINIMO_INTERMITENCIAS = 2
VENTANA = timedelta(days=7)


def analizar_intermitencias(
    filas: list[dict[str, Any]],
    *,
    campo_evento: str,
    ahora: datetime | None = None,
) -> list[dict[str, Any]]:
    """Cuenta eventos unicos por puerto dentro de los ultimos siete dias.

    ``campo_evento`` debe ser el nombre documentado por la fuente para el
    identificador estable del evento. No se deduplica por hora de muestra.
    """
    referencia = ahora or datetime.now(timezone.utc)
    inicio = referencia - VENTANA
    eventos: dict[tuple[str, str], set[str]] = defaultdict(set)

    for fila in filas:
        cmts = fila.get("cmts")
        descripcion = fila.get("descripcion")
        evento_id = fila.get(campo_evento)
        fecha = fila.get("_time")
        if not cmts or not descripcion or evento_id in {None, ""}:
            continue
        if not isinstance(fecha, datetime):
            continue
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=timezone.utc)
        if not inicio <= fecha <= referencia:
            continue
        eventos[(str(cmts), str(descripcion))].add(str(evento_id))

    resultado = [
        {
            "cmts": cmts,
            "puerto": descripcion,
            "cantidad_intermitencias": len(ids),
        }
        for (cmts, descripcion), ids in eventos.items()
        if len(ids) >= MINIMO_INTERMITENCIAS
    ]
    resultado.sort(
        key=lambda item: (
            -item["cantidad_intermitencias"],
            item["cmts"],
            item["puerto"],
        )
    )
    return resultado


def obtener_intermitencias_actuales() -> dict[str, Any]:
    """No infiere un identificador de evento inexistente.

    ``obtener_intermitencias_flux`` queda preparado con la ventana requerida.
    Debe conectarse a ``consultar_flux_temp(..., fuente="cmts")`` cuando se
    documente el campo que identifica cada intermitencia; hasta entonces no es
    posible filtrar ni contar sin confundir muestras con eventos.
    """
    return {"datos": []}
