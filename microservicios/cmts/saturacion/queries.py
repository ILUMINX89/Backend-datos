"""Consultas Flux para saturacion de puertos CMTS."""

from datetime import datetime

from microservicios.config import settings


def obtener_bw_flux() -> str:
    return f"""
from(bucket: "{settings.influx_cmts_bucket}")
  |> range(start: -4d)
  |> filter(fn: (r) => r._measurement == "estado_puertos")
  |> filter(fn: (r) => r._field == "bw")
  |> filter(fn: (r) => exists r.cmts and exists r.descripcion)
  |> group(columns: ["cmts", "descripcion"])
  |> last()
  |> keep(columns: ["_value", "cmts", "descripcion"])
"""


def obtener_utilizacion_flux(inicio: datetime, fin: datetime) -> str:
    return f"""
from(bucket: "{settings.influx_cmts_bucket}")
  |> range(start: time(v: "{inicio.isoformat()}"), stop: time(v: "{fin.isoformat()}"))
  |> filter(fn: (r) => r._measurement == "estado_puertos")
  |> filter(fn: (r) => r._field == "utilizacion")
  |> filter(fn: (r) => exists r.cmts and exists r.descripcion)
  |> keep(columns: ["_value", "cmts", "descripcion"])
"""


def obtener_snr_flux() -> str:
    return f"""
from(bucket: "{settings.influx_cmts_bucket}")
  |> range(start: -4d)
  |> filter(fn: (r) => r._measurement == "estado_puertos")
  |> filter(fn: (r) => r._field == "snr")
  |> filter(fn: (r) => exists r.cmts and exists r.descripcion)
  |> group(columns: ["cmts", "descripcion"])
  |> tail(n: 60)
  |> keep(columns: ["_time", "_value", "cmts", "descripcion"])
"""
