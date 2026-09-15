"""Consulta de temperatura actual por tarjeta OLT."""

from microservicios.config import settings


def obtener_temperatura_actual_flux() -> str:
    return f'''
from(bucket: "{settings.influx_temp_bucket}")
  |> range(start: -10m)
  |> filter(fn: (r) => r._measurement == "Temperatura")
  |> filter(fn: (r) =>
      r._field == "NOMBRE" or
      (r._field == "TEMPERATURA" and r._value != 2147483647)
  )
  |> group(columns: ["OLT", "TARJETA", "_field"])
  |> last()
  |> pivot(
      rowKey: ["OLT", "TARJETA"],
      columnKey: ["_field"],
      valueColumn: "_value"
  )
  |> group(columns: [])
  |> sort(columns: ["OLT", "TARJETA"])
'''
