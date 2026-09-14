"""Ejecuta la consulta de tráfico OLT y muestra el resultado en JSON."""

import json
import sys
from datetime import date, datetime
from typing import Any

from influx import consultar_flux_temp

CONSULTA = """
from(bucket: "trafico_temperatura_olts")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "trafico_olt")
  |> filter(fn: (r) =>
      r._field == "INPUT" or
      r._field == "OUTPUT"
  )
  |> group(columns: ["OLT", "PUERTO", "_field"])
  |> derivative(unit: 1s, nonNegative: true)
  |> map(fn: (r) => ({
      r with
      _value: r._value * 8.0 / 1000.0
  }))
  |> pivot(
      rowKey: ["_time", "OLT", "PUERTO"],
      columnKey: ["_field"],
      valueColumn: "_value"
  )
  |> map(fn: (r) => ({
      r with
      SATURACION:
        if r.INPUT > r.OUTPUT then
          (r.INPUT / 10000000.0) * 100.0
        else
          (r.OUTPUT / 10000000.0) * 100.0
  }))
  |> filter(fn: (r) => r.SATURACION > 70.0)
  |> group(columns: ["OLT", "PUERTO"])
  |> max(column: "SATURACION")
  |> group(columns: [])
  |> sort(columns: ["SATURACION"], desc: true)
"""


def serializar(valor: Any) -> str:
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()

    return str(valor)


def main() -> int:
    try:
        print("Consultando InfluxDB...")

        datos = consultar_flux_temp(CONSULTA)

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Registros encontrados: {len(datos)}")

    print(
        json.dumps(
            {
                "cantidad": len(datos),
                "datos": datos,
            },
            ensure_ascii=False,
            indent=2,
            default=serializar,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
