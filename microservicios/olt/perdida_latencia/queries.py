"""Consultas Flux de pérdida y latencia por equipo OLT."""

import re

from microservicios.config import settings


EQUIPO_VALIDO = re.compile(r"^[A-Za-z0-9_.:-]+$")
PERIODOS_PERMITIDOS = {
    "-10m",
    "-1h",
    "-6h",
    "-12h",
    "-24h",
    "-7d",
    "-30d",
}


def _validar_equipo(equipo: str) -> str:
    equipo = equipo.strip()
    if not equipo or EQUIPO_VALIDO.fullmatch(equipo) is None:
        raise ValueError("Equipo inválido")
    return equipo


def _validar_periodo(periodo: str) -> str:
    if periodo not in PERIODOS_PERMITIDOS:
        raise ValueError("Periodo de latencia no permitido")
    return periodo


def obtener_latencia_equipo_flux(
    equipo: str,
    periodo: str = "-30d",
) -> str:
    equipo = _validar_equipo(equipo)
    periodo = _validar_periodo(periodo)

    return f'''from(bucket: "{settings.influx_red_bucket}")
  |> range(start: {periodo})
  |> filter(fn: (r) => r._measurement == "ping_monitor")
  |> filter(fn: (r) => r._field == "latency")
  |> filter(fn: (r) => r.equipo == "{equipo}")
  |> sort(columns: ["_time"])
'''


def obtener_latencia_actual_flux() -> str:
    return f'''from(bucket: "{settings.influx_red_bucket}")
  |> range(start: -10m)
  |> filter(fn: (r) => r._measurement == "ping_monitor")
  |> filter(fn: (r) =>
      r._field == "latency" or r._field == "packet_loss"
  )
  |> group(columns: ["equipo", "_field"])
  |> last()
  |> group(columns: [])
  |> sort(columns: ["equipo", "_field"])
'''
