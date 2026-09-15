"""Consultas Flux del dominio de alarmas."""

from microservicios.config import settings


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
from(bucket: "{settings.influx_temp_bucket}")
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


def obtener_saturacion_flux() -> str:
    """
    Puertos que superaron el 25% de utilización
    durante las últimas 24 horas.

    Capacidad asumida del puerto: 10 Gbps.
    """

    return f"""
from(bucket: "{settings.influx_temp_bucket}")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "trafico_olt")
  |> filter(fn: (r) =>
      r._field == "INPUT" or
      r._field == "OUTPUT"
  )
  |> group(columns: ["OLT", "PUERTO", "_field"])
  |> derivative(unit: 1s, nonNegative: true)
  |> map(fn: (r) => ({{
      r with
      _value: r._value * 8.0 / 1000.0
  }}))
  |> pivot(
      rowKey: ["_time", "OLT", "PUERTO"],
      columnKey: ["_field"],
      valueColumn: "_value"
  )
  |> map(fn: (r) => ({{
      r with
      SATURACION:
        if r.INPUT > r.OUTPUT then
          (r.INPUT / 10000000.0) * 100.0
        else
          (r.OUTPUT / 10000000.0) * 100.0
  }}))
  |> filter(fn: (r) => r.SATURACION > 70.0)
  |> group(columns: ["OLT", "PUERTO"])
  |> max(column: "SATURACION")
  |> group(columns: [])
  |> sort(columns: ["SATURACION"], desc: true)
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
