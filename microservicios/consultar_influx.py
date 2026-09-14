"""Ejecuta la consulta de tráfico OLT y muestra el resultado en JSON."""

import json
import sys
from datetime import date, datetime
from typing import Any

from influx import consultar_flux

CONSULTA = """from(bucket: "Monitor_Red_Claro")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "ping_monitor")
  |> filter(fn: (r) => r._field == "packet_loss")"""


def serializar(valor: Any) -> str:
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    return str(valor)


def main() -> int:
    try:
        datos = consultar_flux(CONSULTA)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {"cantidad": len(datos), "datos": datos},
            ensure_ascii=False,
            indent=2,
            default=serializar,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
