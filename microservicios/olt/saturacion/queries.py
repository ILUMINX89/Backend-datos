"""Consultas Flux para saturacion de puertos OLT."""

from microservicios.config import settings


def obtener_saturacion_flux() -> str:
    """Devuelve la secuencia de muestras con saturacion superior al 70 %."""
    return f'''
from(bucket: "{settings.influx_temp_bucket}")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "trafico_olt")
  |> filter(fn: (r) => r._field == "INPUT" or r._field == "OUTPUT")
  |> group(columns: ["OLT", "PUERTO", "_field"])
  |> derivative(unit: 1s, nonNegative: true)
  |> map(fn: (r) => ({{r with _value: r._value * 8.0 / 1000.0}}))
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
  |> group(columns: [])
  |> sort(columns: ["OLT", "PUERTO", "_time"])
'''
