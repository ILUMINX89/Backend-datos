"""Consultas Flux del dominio de alarmas.

El esquema definitivo aun no esta documentado. Las consultas reales deben vivir
en este modulo cuando se confirmen measurement, fields y tags.
"""


def obtener_alarmas_flux(*, tipo: int | None, estado: str | None, limit: int) -> str:
    del tipo, estado, limit
    raise NotImplementedError(
        "TODO: completar la consulta con el measurement, fields y tags reales"
    )


def obtener_tendencia_flux(*, horas: int) -> str:
    del horas
    raise NotImplementedError("TODO: completar la consulta de tendencia real")


def obtener_top_flux(*, limit: int) -> str:
    del limit
    raise NotImplementedError("TODO: completar la consulta de top de alarmas real")


def obtener_alarma_por_id_flux(alarma_id: str) -> str:
    del alarma_id
    raise NotImplementedError("TODO: completar la consulta de detalle real")
