"""Consultas Flux para detectar caídas de puertos OLT por tráfico."""

from microservicios.config import settings


def obtener_caidas_flux(
    periodo: str = "-7d",
) -> str:
    """
    Consulta histórica de tráfico.

    Se usa para reconstruir caídas en Python.
    """

    periodos_permitidos = {
        "-24h",
        "-2d",
        "-4d",
        "-7d",
    }

    if periodo not in periodos_permitidos:
        raise ValueError("Periodo de caídas no permitido. " "Use -24h, -2d, -4d o -7d.")

    return f"""
from(bucket: "{settings.influx_temp_bucket}")

  |> range(start: {periodo})

  |> filter(fn: (r) =>
      r._measurement == "trafico_olt"
  )

  |> filter(fn: (r) =>
      r._field == "INPUT" or
      r._field == "OUTPUT"
  )

  |> group(
      columns: [
          "OLT",
          "PUERTO",
          "_field"
      ]
  )

  |> derivative(
      unit: 1s,
      nonNegative: true
  )

  |> map(fn: (r) => ({{
      r with
      _value: r._value * 8.0 / 1000.0
  }}))

  |> pivot(
      rowKey: [
          "_time",
          "OLT",
          "PUERTO"
      ],
      columnKey: ["_field"],
      valueColumn: "_value"
  )

  |> map(fn: (r) => ({{
      r with
      TRAFICO:
        if exists r.INPUT and exists r.OUTPUT then
          if r.INPUT > r.OUTPUT then
            r.INPUT
          else
            r.OUTPUT
        else if exists r.INPUT then
          r.INPUT
        else if exists r.OUTPUT then
          r.OUTPUT
        else
          0.0
  }}))

  |> keep(
      columns: [
          "_time",
          "OLT",
          "PUERTO",
          "INPUT",
          "OUTPUT",
          "TRAFICO"
      ]
  )

  |> group(
      columns: [
          "OLT",
          "PUERTO"
      ]
  )

  |> sort(
      columns: ["_time"]
  )

  |> group(columns: [])
"""


def obtener_estado_actual_flux() -> str:
    """
    Obtiene las últimas muestras de tráfico recientes.

    Se revisan 30 minutos para detectar:
    - puertos con tráfico actual;
    - puertos con dos muestras seguidas en 0;
    - puertos que todavía están reportando pero sin tráfico.
    """

    return f"""
from(bucket: "{settings.influx_temp_bucket}")

  |> range(start: -30m)

  |> filter(fn: (r) =>
      r._measurement == "trafico_olt"
  )

  |> filter(fn: (r) =>
      r._field == "INPUT" or
      r._field == "OUTPUT"
  )

  |> group(
      columns: [
          "OLT",
          "PUERTO",
          "_field"
      ]
  )

  |> derivative(
      unit: 1s,
      nonNegative: true
  )

  |> map(fn: (r) => ({{
      r with
      _value: r._value * 8.0 / 1000.0
  }}))

  |> pivot(
      rowKey: [
          "_time",
          "OLT",
          "PUERTO"
      ],
      columnKey: ["_field"],
      valueColumn: "_value"
  )

  |> map(fn: (r) => ({{
      r with
      TRAFICO:
        if exists r.INPUT and exists r.OUTPUT then
          if r.INPUT > r.OUTPUT then
            r.INPUT
          else
            r.OUTPUT
        else if exists r.INPUT then
          r.INPUT
        else if exists r.OUTPUT then
          r.OUTPUT
        else
          0.0
  }}))

  |> keep(
      columns: [
          "_time",
          "OLT",
          "PUERTO",
          "INPUT",
          "OUTPUT",
          "TRAFICO"
      ]
  )

  |> group(
      columns: [
          "OLT",
          "PUERTO"
      ]
  )

  |> sort(
      columns: ["_time"]
  )

  |> tail(n: 3)

  |> group(columns: [])

  |> sort(
      columns: [
          "OLT",
          "PUERTO",
          "_time"
      ]
  )
"""


def obtener_ultima_muestra_conocida_flux(
    periodo: str = "-7d",
) -> str:
    """
    Obtiene la última muestra conocida de cada puerto.

    Sirve para detectar puertos que dejaron de reportar
    completamente y por eso no aparecen en los últimos 30 minutos.
    """

    periodos_permitidos = {
        "-2d",
        "-4d",
        "-7d",
    }

    if periodo not in periodos_permitidos:
        raise ValueError("Periodo de búsqueda no permitido.")

    return f"""
from(bucket: "{settings.influx_temp_bucket}")

  |> range(start: {periodo})

  |> filter(fn: (r) =>
      r._measurement == "trafico_olt"
  )

  |> filter(fn: (r) =>
      r._field == "INPUT" or
      r._field == "OUTPUT"
  )

  |> group(
      columns: [
          "OLT",
          "PUERTO",
          "_field"
      ]
  )

  |> derivative(
      unit: 1s,
      nonNegative: true
  )

  |> map(fn: (r) => ({{
      r with
      _value: r._value * 8.0 / 1000.0
  }}))

  |> pivot(
      rowKey: [
          "_time",
          "OLT",
          "PUERTO"
      ],
      columnKey: ["_field"],
      valueColumn: "_value"
  )

  |> map(fn: (r) => ({{
      r with
      TRAFICO:
        if exists r.INPUT and exists r.OUTPUT then
          if r.INPUT > r.OUTPUT then
            r.INPUT
          else
            r.OUTPUT
        else if exists r.INPUT then
          r.INPUT
        else if exists r.OUTPUT then
          r.OUTPUT
        else
          0.0
  }}))

  |> keep(
      columns: [
          "_time",
          "OLT",
          "PUERTO",
          "INPUT",
          "OUTPUT",
          "TRAFICO"
      ]
  )

  |> group(
      columns: [
          "OLT",
          "PUERTO"
      ]
  )

  |> sort(
      columns: ["_time"]
  )

  |> tail(n: 1)

  |> group(columns: [])

  |> sort(
      columns: [
          "OLT",
          "PUERTO"
      ]
  )
"""


def _escapar_flux(
    valor: str,
) -> str:
    return valor.replace("\\", "\\\\").replace('"', '\\"')


def obtener_ultima_actividad_flux(
    puertos: list[tuple[str, str]],
    periodo: str = "-7d",
) -> str:
    """
    Busca la última muestra con tráfico > 0
    para los puertos actualmente problemáticos.
    """

    periodos_permitidos = {
        "-2d",
        "-4d",
        "-7d",
    }

    if periodo not in periodos_permitidos:
        raise ValueError("Periodo de búsqueda no permitido.")

    if not puertos:
        raise ValueError("No se recibieron puertos para consultar.")

    condiciones = []

    for olt, puerto in puertos:
        olt_seguro = _escapar_flux(olt)

        puerto_seguro = _escapar_flux(puerto)

        condiciones.append(
            (f'(r.OLT == "{olt_seguro}" ' f'and r.PUERTO == "{puerto_seguro}")')
        )

    filtro_puertos = " or ".join(condiciones)

    return f"""
from(bucket: "{settings.influx_temp_bucket}")

  |> range(start: {periodo})

  |> filter(fn: (r) =>
      r._measurement == "trafico_olt"
  )

  |> filter(fn: (r) =>
      r._field == "INPUT" or
      r._field == "OUTPUT"
  )

  |> filter(fn: (r) =>
      {filtro_puertos}
  )

  |> group(
      columns: [
          "OLT",
          "PUERTO",
          "_field"
      ]
  )

  |> derivative(
      unit: 1s,
      nonNegative: true
  )

  |> map(fn: (r) => ({{
      r with
      _value: r._value * 8.0 / 1000.0
  }}))

  |> pivot(
      rowKey: [
          "_time",
          "OLT",
          "PUERTO"
      ],
      columnKey: ["_field"],
      valueColumn: "_value"
  )

  |> map(fn: (r) => ({{
      r with
      TRAFICO:
        if exists r.INPUT and exists r.OUTPUT then
          if r.INPUT > r.OUTPUT then
            r.INPUT
          else
            r.OUTPUT
        else if exists r.INPUT then
          r.INPUT
        else if exists r.OUTPUT then
          r.OUTPUT
        else
          0.0
  }}))

  |> filter(fn: (r) =>
      r.TRAFICO > 0.0
  )

  |> keep(
      columns: [
          "_time",
          "OLT",
          "PUERTO",
          "INPUT",
          "OUTPUT",
          "TRAFICO"
      ]
  )

  |> group(
      columns: [
          "OLT",
          "PUERTO"
      ]
  )

  |> sort(
      columns: ["_time"]
  )

  |> tail(n: 1)

  |> group(columns: [])

  |> sort(
      columns: [
          "OLT",
          "PUERTO"
      ]
  )
"""
