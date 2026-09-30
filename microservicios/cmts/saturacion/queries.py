"""Consultas Flux para saturacion de puertos CMTS."""

from datetime import datetime

from microservicios.config import settings


def obtener_muestras_flux(inicio: datetime, fin: datetime, campos: tuple[str, ...] = ("bw", "utilizacion", "snr", "portadoras")) -> str:
    permitidos = {"bw", "utilizacion", "snr", "portadoras"}
    if not campos or any(campo not in permitidos for campo in campos):
        raise ValueError("Campos HFC no permitidos")
    filtro = " or ".join(f'r._field == "{campo}"' for campo in campos)
    return f"""
import "strings"

from(bucket: "{settings.influx_cmts_bucket}")
  |> range(
      start: time(v: "{inicio.isoformat()}"),
      stop: time(v: "{fin.isoformat()}")
  )
  |> filter(fn: (r) => r._measurement == "estado_puertos")
  |> filter(fn: (r) => {filtro})
  |> filter(fn: (r) => exists r.cmts and exists r.puerto and exists r.descripcion)
  |> filter(fn: (r) => strings.hasPrefix(v: r.descripcion, prefix: "NODO "))
  |> keep(columns: ["_time", "_field", "_value", "cmts", "puerto", "descripcion"])
"""
