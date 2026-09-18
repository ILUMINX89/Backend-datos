"""Consultas Flux para saturacion de puertos CMTS."""

from microservicios.config import settings


def _metricas_recientes_flux(campo: str, cantidad: int | None = None) -> str:
    limite = f"  |> limit(n: {cantidad})\n" if cantidad is not None else ""
    return f'''
from(bucket: "{settings.influx_cmts_bucket}")
  |> range(start: -30m)
  |> filter(fn: (r) => r._measurement == "estado_puertos")
  |> filter(fn: (r) => r._field == "{campo}")
  |> filter(fn: (r) => exists r.cmts and exists r.descripcion)
  |> group(columns: ["cmts", "descripcion"])
  |> sort(columns: ["_time"], desc: true)
{limite}  |> keep(columns: ["_time", "_value", "cmts", "descripcion"])
'''


def obtener_bw_flux() -> str:
    return _metricas_recientes_flux("bw", 1)


def obtener_utilizacion_flux() -> str:
    # Para criticidad se necesitan todos los puntos de la ventana, no solo 3.
    return _metricas_recientes_flux("utilizacion")


def obtener_snr_flux() -> str:
    return _metricas_recientes_flux("snr", 3)
