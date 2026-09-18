"""Consultas Flux para detectar nodos en puertos CMTS duplicados."""

from microservicios.config import settings


def obtener_puertos_duplicados_flux() -> str:
    """Obtiene la ubicacion mas reciente de cada descripcion, CMTS y puerto."""
    return f"""
from(bucket: "{settings.influx_cmts_bucket}")
  |> range(start: -1h)
  |> filter(fn: (r) =>
      r._measurement == "estado_puertos" and
      r._field == "cm_registrados"
  )
  |> filter(fn: (r) =>
      exists r.cmts and
      exists r.puerto and
      exists r.descripcion
  )
  |> group(columns: ["cmts", "puerto", "descripcion"])
  |> last()
  |> keep(columns: ["_time", "cmts", "puerto", "descripcion"])
"""
