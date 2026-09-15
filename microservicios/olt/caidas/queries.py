"""Consultas Flux para estados de puertos OLT."""

from microservicios.config import settings


def obtener_caidas_flux(periodo: str = "-7d") -> str:
    """Devuelve estados ordenados para reconstruir caidas en Python."""
    if periodo not in {"-7d", "-24h"}:
        raise ValueError("Periodo de caidas no permitido")

    return f'''
from(bucket: "{settings.influx_temp_bucket}")
  |> range(start: {periodo})
  |> filter(fn: (r) => r._measurement == "trafico_olt")
  |> filter(fn: (r) => r._field == "ESTADO")
  |> keep(columns: ["_time", "_value", "OLT", "PUERTO"])
  |> rename(columns: {{_value: "ESTADO"}})
  |> group(columns: ["OLT", "PUERTO"])
  |> sort(columns: ["_time"])
  |> group(columns: [])
'''
