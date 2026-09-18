"""Consultas Flux para detectar intermitencias HFC."""

from microservicios.config import settings


def obtener_intermitencias_flux(
    periodo: str = "-12d",
) -> str:
    """
    Detecta caídas de puertos HFC usando cm_registrados.

    Una caída se confirma cuando existen 2 muestras consecutivas
    con cm_registrados en 0.

    stateCount permite que una secuencia:

        20, 0, 0, 0, 0, 15

    genere solamente un evento, porque únicamente conservamos
    la muestra donde el contador llega exactamente a 2.

    IMPORTANTE:
    Por seguridad empezamos probando solamente 1 hora.
    """

    periodos_permitidos = {
        "-1h",
        "-24h",
        "-12d",
    }

    if periodo not in periodos_permitidos:
        raise ValueError(
            "Periodo de intermitencias no permitido. " "Use -1h, -24h o -7d."
        )

    return f"""
from(bucket: "{settings.influx_cmts_bucket}")
  |> range(start: {periodo})

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

  |> filter(fn: (r) =>
      r.descripcion =~ /^NODO /
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

  |> stateCount(
      fn: (r) => float(v: r._value) <= 0.0,
      column: "muestras_cero"
  )

  |> filter(fn: (r) =>
      r.muestras_cero == 2
  )

  |> group(
      columns: [
          "cmts",
          "puerto",
          "descripcion"
      ]
  )

  |> count(
      column: "muestras_cero"
  )

  |> rename(
      columns: {{
          muestras_cero: "cantidad_intermitencias"
      }}
  )

  |> filter(fn: (r) =>
      r.cantidad_intermitencias >= 2
  )

  |> keep(
      columns: [
          "cmts",
          "puerto",
          "descripcion",
          "cantidad_intermitencias"
      ]
  )

  |> group(columns: [])

  |> sort(
      columns: ["cantidad_intermitencias"],
      desc: true
  )
"""
