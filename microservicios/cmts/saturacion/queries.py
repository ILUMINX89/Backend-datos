"""Consultas Flux para saturacion de puertos CMTS."""

from datetime import datetime

from microservicios.config import settings


def obtener_muestras_flux(inicio: datetime, fin: datetime) -> str:
    return f"""
from(bucket: "{settings.influx_cmts_bucket}")
  |> range(
      start: time(v: "{inicio.isoformat()}"),
      stop: time(v: "{fin.isoformat()}")
  )
  |> filter(fn: (r) => r._measurement == "estado_puertos")
  |> filter(fn: (r) => r._field == "bw" or r._field == "utilizacion")
  |> filter(fn: (r) => exists r.cmts and exists r.puerto and exists r.descripcion)
  |> keep(columns: ["_time", "_field", "_value", "cmts", "puerto", "descripcion"])
"""
