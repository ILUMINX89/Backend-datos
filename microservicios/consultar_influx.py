"""Herramienta interactiva para probar manualmente los servicios OLT."""

import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

# Compatibilidad con: python .\microservicios\consultar_influx.py
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from microservicios.olt.caidas.service import obtener_caidas
from microservicios.olt.correlacion.service import obtener_correlacion
from microservicios.olt.crc.service import obtener_crc
from microservicios.olt.saturacion.service import obtener_saturacion

# Alias temporales para consumidores que usaban los nombres anteriores.
consultar_saturacion = obtener_saturacion
consultar_caidas = obtener_caidas
consultar_crc = obtener_crc
consultar_correlacion = obtener_correlacion


def serializar(valor: Any) -> str:
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    return str(valor)


def imprimir_resultado(resultado: dict[str, Any]) -> None:
    print(json.dumps(resultado, ensure_ascii=False, indent=2, default=serializar))


def mostrar_menu() -> None:
    print()
    print("=" * 55)
    print(" MONITOR OLT - CONSULTAS INFLUXDB")
    print("=" * 55)
    print("1. Saturación de puertos")
    print("2. Caídas recurrentes / mayores a 2 horas")
    print("3. Errores CRC mayores a 10/s")
    print("4. Correlación Saturación + CRC + Caídas")
    print("0. Salir")
    print("=" * 55)


def ejecutar_caidas() -> dict[str, Any]:
    periodo = seleccionar_periodo_caidas()

    if periodo is None:
        return {
            "consulta": "caidas",
            "cancelado": True,
            "mensaje": "Consulta cancelada por el usuario",
        }

    return obtener_caidas(periodo)


def main() -> int:
    opciones: dict[str, Callable[[], dict[str, Any]]] = {
        "1": obtener_saturacion,
        "2": obtener_caidas,
        "3": obtener_crc,
        "4": obtener_correlacion,
    }

    while True:
        mostrar_menu()
        opcion = input("Seleccione una opción: ").strip()

        if opcion == "0":
            print("Saliendo...")
            return 0

        servicio = opciones.get(opcion)
        if servicio is None:
            print("Opción no válida.")
            continue

        try:
            imprimir_resultado(servicio())
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)


def seleccionar_periodo_caidas():
    print()
    print("Periodo para revisar caídas")
    print("1. 2 días")
    print("2. 4 días")
    print("3. 7 días")
    print("0. Volver")
    print()

    opcion = input("Seleccione periodo: ").strip()

    periodos = {
        "1": "-2d",
        "2": "-4d",
        "3": "-7d",
    }

    return periodos.get(opcion)


if __name__ == "__main__":
    raise SystemExit(main())
