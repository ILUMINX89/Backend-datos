"""Consultas Flux para saturacion de puertos CMTS."""

from microservicios.config import settings


def _ultima_metrica_flux(campo: str) -> str:
    return f'''
from(bucket: "{settings.influx_cmts_bucket}")
  |> range(start: -30m)
  |> filter(fn: (r) => r._measurement == "estado_puertos")
  |> filter(fn: (r) => r._field == "{campo}")
  |> filter(fn: (r) => exists r.cmts and exists r.descripcion)
  |> group(columns: ["cmts", "descripcion"])
  |> last()
  |> keep(columns: ["_time", "_value", "cmts", "descripcion"])
'''


def obtener_bw_flux() -> str:
    return _ultima_metrica_flux("bw")


def obtener_utilizacion_flux() -> str:
    return _ultima_metrica_flux("utilizacion")
