"""Consultas Flux para intermitencias HFC."""

from microservicios.config import settings


def obtener_intermitencias_flux() -> str:
    """
    Detecta caídas confirmadas durante los últimos 7 días.

    Criterio equivalente al usado en OLT:
    - primero debe existir estado operativo: cm_registrados > 0
    - 2 muestras consecutivas con cm_registrados == 0
      confirman una caída
    - cuando vuelve a > 0, el contador de ceros se reinicia

    Flux devuelve únicamente una fila por caída confirmada para
    evitar transferir a Python todo el histórico de 7 días.
    """

    return f"""
from(bucket: "{settings.influx_cmts_bucket}")

  |> range(start: -7d)

  |> filter(fn: (r) =>
      r._measurement == "estado_puertos"
  )

  |> filter(fn: (r) =>
      r._field == "cm_registrados"
  )

  |> filter(fn: (r) =>
      exists r.cmts and
      exists r.puerto and
      exists r.descripcion
  )

  |> keep(
      columns: [
          "_time",
          "_value",
          "cmts",
          "puerto",
          "descripcion"
      ]
  )

  |> group(
      columns: [
          "cmts",
          "puerto",
          "descripcion"
      ]
  )

  |> sort(
      columns: ["_time"]
  )

  |> map(fn: (r) => ({{
      r with
      operativo_visto:
          if r._value > 0 then 1
          else 0
  }}))

  |> cumulativeSum(
      columns: ["operativo_visto"]
  )

  |> stateTracking(
      fn: (r) => r._value == 0,
      countColumn: "muestras_cero"
  )

  |> filter(fn: (r) =>
      r.operativo_visto > 0 and
      r.muestras_cero == 2
  )

  |> keep(
      columns: [
          "_time",
          "cmts",
          "puerto",
          "descripcion"
      ]
  )

  |> group(columns: [])

  |> sort(
      columns: [
          "cmts",
          "puerto",
          "descripcion",
          "_time"
      ]
  )
"""
