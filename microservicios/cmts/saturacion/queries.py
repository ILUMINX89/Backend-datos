"""Consultas Flux para saturacion de puertos CMTS."""

from microservicios.config import settings


def _metricas_recientes_flux(campo: str, cantidad: int | None = None) -> str:
    limite = f"  |> limit(n: {cantidad})\n" if cantidad is not None else ""
    return f"""
from(bucket: "{settings.influx_cmts_bucket}")
  |> range(start: -1d)
  |> filter(fn: (r) => r._measurement == "estado_puertos")
  |> filter(fn: (r) => r._field == "{campo}")
  |> filter(fn: (r) => exists r.cmts and exists r.descripcion)
  |> group(columns: ["cmts", "descripcion"])
  |> sort(columns: ["_time"], desc: true)
{limite}  |> keep(columns: ["_time", "_value", "cmts", "descripcion"])
"""


def obtener_bw_flux() -> str:
    return _metricas_recientes_flux("bw", 1)


def obtener_utilizacion_flux() -> str:
    """Agrega en Influx la utilizacion de cuatro dias por CMTS/puerto."""
    return f"""
bw = from(bucket: "{settings.influx_cmts_bucket}")
  |> range(start: -1d)
  |> filter(fn: (r) => r._measurement == "estado_puertos")
  |> filter(fn: (r) => r._field == "bw")
  |> filter(fn: (r) => exists r.cmts and exists r.descripcion)
  |> group(columns: ["cmts", "descripcion"])
  |> last()
  |> map(fn: (r) => ({{r with bw: float(v: r._value)}}))
  |> keep(columns: ["cmts", "descripcion", "bw"])

utilizacion = from(bucket: "{settings.influx_cmts_bucket}")
  |> range(start: -1d)
  |> filter(fn: (r) => r._measurement == "estado_puertos")
  |> filter(fn: (r) => r._field == "utilizacion")
  |> filter(fn: (r) => exists r.cmts and exists r.descripcion)
  |> group(columns: ["cmts", "descripcion"])
  |> keep(columns: ["_time", "_value", "cmts", "descripcion"])

join(tables: {{utilizacion: utilizacion, bw: bw}}, on: ["cmts", "descripcion"])
  |> filter(fn: (r) => r.bw > 0.0)
  |> map(fn: (r) => ({{
      cmts: r.cmts,
      descripcion: r.descripcion,
      bw: r.bw,
      porcentaje: if (float(v: r._value) / r.bw * 100.0) < 0.0 then 0.0
        else if (float(v: r._value) / r.bw * 100.0) > 100.0 then 100.0
        else float(v: r._value) / r.bw * 100.0,
  }}))
  |> group(columns: ["cmts", "descripcion"])
  |> reduce(
      identity: {{muestras_analizadas: 0, puntos_sobre_90: 0, suma_sobre_90: 0.0, suma_total: 0.0, bw: 0.0}},
      fn: (r, accumulator) => ({{
          muestras_analizadas: accumulator.muestras_analizadas + 1,
          puntos_sobre_90: accumulator.puntos_sobre_90 + (if r.porcentaje >= 90.0 then 1 else 0),
          suma_sobre_90: accumulator.suma_sobre_90 + (if r.porcentaje >= 90.0 then r.porcentaje else 0.0),
          suma_total: accumulator.suma_total + r.porcentaje,
          bw: r.bw,
      }}),
  )
  |> map(fn: (r) => ({{
      r with
      promedio_sobre_90: if r.puntos_sobre_90 > 0 then r.suma_sobre_90 / float(v: r.puntos_sobre_90) else 0.0,
      promedio_total: if r.muestras_analizadas > 0 then r.suma_total / float(v: r.muestras_analizadas) else 0.0,
  }}))
  |> keep(columns: ["cmts", "descripcion", "bw", "muestras_analizadas", "puntos_sobre_90", "promedio_sobre_90", "promedio_total"])
"""


def obtener_snr_flux() -> str:
    return _metricas_recientes_flux("snr", 60)
