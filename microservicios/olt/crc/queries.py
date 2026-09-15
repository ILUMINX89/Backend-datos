"""Consultas Flux para errores CRC de puertos OLT."""

from microservicios.config import settings


def _metricas_crc_flux(ventana: str) -> str:
    return f'''
from(bucket: "{settings.influx_temp_bucket}")
  |> range(start: {ventana})
  |> filter(fn: (r) => r._measurement == "trafico_olt")
  |> filter(fn: (r) => r._field == "CRC")
  |> group(columns: ["OLT", "PUERTO", "_field"])
  |> derivative(unit: 1s, nonNegative: true)
  |> rename(columns: {{_value: "CRC_POR_SEGUNDO"}})
'''


def obtener_crc_flux() -> str:
    """Devuelve muestras superiores a diez errores CRC por segundo."""
    return _metricas_crc_flux("-24h") + '''
  |> filter(fn: (r) => r.CRC_POR_SEGUNDO > 10.0)
  |> group(columns: [])
  |> sort(columns: ["OLT", "PUERTO", "_time"])
'''


def obtener_crc_actual_flux() -> str:
    """Filtra el umbral despues de seleccionar la ultima muestra de cada puerto."""
    return _metricas_crc_flux("-15m") + '''
  |> group(columns: ["OLT", "PUERTO"])
  |> sort(columns: ["_time"])
  |> last(column: "CRC_POR_SEGUNDO")
  |> filter(fn: (r) => r.CRC_POR_SEGUNDO > 10.0)
'''
