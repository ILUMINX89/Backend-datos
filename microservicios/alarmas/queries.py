"""Consultas Flux del dominio de alarmas.

El esquema definitivo aun no esta documentado. Las consultas reales deben vivir
en este modulo cuando se confirmen measurement, fields y tags.
"""

"""Consultas Flux del dominio de alarmas."""


def obtener_alarmas_flux(
    *,
    tipo: int | None,
    estado: str | None,
    limit: int,
) -> str:
    """
    Consulta inicial para detectar puertos con estado anómalo.

    Regla actual:
    ESTADO == 6  -> normal
    ESTADO != 6  -> candidato a alarma

    La clasificación Tipo 1 / Tipo 2 / Tipo 3 se hará después
    en alarmas_service.py.
    """

    del tipo, estado

    return f"""
from(bucket: "trafico_temperatura_olts")
  |> range(start: -10m)
  |> filter(fn: (r) => r._measurement == "trafico_olt")
  |> filter(fn: (r) =>
      r._field == "DESCRIPCION" or
      r._field == "TX" or
      r._field == "RX" or
      r._field == "ESTADO"
  )
  |> group(columns: ["OLT", "PUERTO", "_field"])
  |> last()
  |> pivot(
      rowKey: ["OLT", "PUERTO"],
      columnKey: ["_field"],
      valueColumn: "_value"
  )
  |> filter(fn: (r) => r.DESCRIPCION != ".")
  |> filter(fn: (r) => r.DESCRIPCION != " ")
  |> filter(fn: (r) => r.ESTADO != 6)
  |> group(columns: [])
  |> sort(columns: ["PUERTO"])
  |> limit(n: {limit})
"""


def obtener_tendencia_flux(*, horas: int) -> str:
    del horas
    raise NotImplementedError("TODO: completar la consulta de tendencia real")


def obtener_top_flux(*, limit: int) -> str:
    del limit
    raise NotImplementedError("TODO: completar la consulta de top de alarmas real")


def obtener_alarma_por_id_flux(alarma_id: str) -> str:
    del alarma_id
    raise NotImplementedError("TODO: completar la consulta de detalle real")
