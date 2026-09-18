"""Consultas Flux para intermitencias HFC."""

from microservicios.config import settings


def obtener_intermitencias_flux() -> str:
    """Consulta la ventana requerida sin suponer el esquema del evento.

    La fuente aun no documenta el measurement/campo que representa una
    intermitencia ni un identificador que permita deduplicar sus muestras.
    Esos filtros deben agregarse cuando el contrato del bucket los defina.
    """
    return f'''
from(bucket: "{settings.influx_cmts_bucket}")
  |> range(start: -7d)
'''
