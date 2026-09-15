"""Consultas Flux para detectar caídas de puertos OLT por tráfico."""

from microservicios.config import settings


def obtener_caidas_flux(
    periodo: str = "-7d",
) -> str:
    """
    Devuelve tráfico INPUT / OUTPUT ordenado por OLT y PUERTO
    para reconstruir caídas en Python.

    Regla de negocio posterior:
    - el puerto venía reportando tráfico;
    - luego tiene 2 muestras consecutivas con tráfico en 0;
    - cada muestra llega aproximadamente cada 5 minutos;
    - con 2 muestras consecutivas en 0 se confirma la caída;
    - cuando vuelve tráfico > 0, termina la caída.
    """

    if periodo not in {
        "-2d",
        "-4d",
        "-7d",
        "-24h",
    }:
        raise ValueError("Periodo de caidas no permitido")

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
        if r.INPUT > r.OUTPUT then
          r.INPUT
        else
          r.OUTPUT
  }}))

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
