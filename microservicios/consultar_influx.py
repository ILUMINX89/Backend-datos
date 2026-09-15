"""Herramienta interactiva para probar manualmente los servicios OLT."""

import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Callable

# Compatibilidad con:
#
# python .\microservicios\consultar_influx.py
#
# Forma recomendada:
#
# python -m microservicios.consultar_influx

if __package__ in {
    None,
    "",
}:
    sys.path.insert(
        0,
        str(Path(__file__).resolve().parents[1]),
    )


from microservicios.olt.caidas.service import (
    obtener_caidas,
    obtener_caidas_actuales,
    obtener_intermitencias,
)
from microservicios.olt.correlacion.service import (
    obtener_correlacion,
)
from microservicios.olt.crc.service import (
    obtener_crc,
)
from microservicios.olt.saturacion.service import (
    obtener_saturacion,
)

# ============================================================
# ALIAS TEMPORALES
# ============================================================

consultar_saturacion = obtener_saturacion

consultar_caidas = obtener_caidas

consultar_crc = obtener_crc

consultar_correlacion = obtener_correlacion


# ============================================================
# SALIDA JSON
# ============================================================


def serializar(
    valor: Any,
) -> str:

    if isinstance(
        valor,
        (
            date,
            datetime,
        ),
    ):
        return valor.isoformat()

    return str(valor)


def imprimir_resultado(
    resultado: dict[str, Any],
) -> None:

    print(
        json.dumps(
            resultado,
            ensure_ascii=False,
            indent=2,
            default=serializar,
        )
    )


# ============================================================
# MENÚ PRINCIPAL
# ============================================================


def mostrar_menu() -> None:

    print()

    print("=" * 55)

    print(" MONITOR OLT - CONSULTAS INFLUXDB")

    print("=" * 55)

    print("1. Saturación de puertos")

    print("2. Caídas de puertos")

    print("3. Errores CRC mayores a 10/s")

    print("4. Correlación Saturación + CRC + Caídas")

    print("5. Intermitencias")

    print("0. Salir")

    print("=" * 55)


# ============================================================
# MENÚ DE CAÍDAS
# ============================================================


def seleccionar_periodo_caidas() -> str | None:

    while True:

        print()

        print("=" * 55)

        print(" CAÍDAS OLT")

        print("=" * 55)

        print("1. Caídas actuales")

        print("2. Últimos 2 días")

        print("3. Últimos 4 días")

        print("4. Últimos 7 días")

        print("0. Volver")

        print("=" * 55)

        opcion = input("Seleccione una opción: ").strip()

        opciones = {
            "1": "actuales",
            "2": "-2d",
            "3": "-4d",
            "4": "-7d",
        }

        if opcion == "0":
            return None

        periodo = opciones.get(opcion)

        if periodo is None:

            print("Opción no válida.")

            continue

        return periodo


def ejecutar_caidas() -> dict[str, Any]:

    periodo = seleccionar_periodo_caidas()

    if periodo is None:

        return {
            "consulta": "caidas",
            "cancelado": True,
            "mensaje": ("Consulta cancelada " "por el usuario"),
        }

    if periodo == "actuales":

        return obtener_caidas_actuales()

    return obtener_caidas(periodo)


# ============================================================
# MENÚ DE INTERMITENCIAS
# ============================================================


def seleccionar_periodo_intermitencias() -> str | None:

    while True:

        print()

        print("=" * 55)

        print(" INTERMITENCIAS OLT")

        print("=" * 55)

        print("1. Últimos 2 días")

        print("2. Últimos 4 días")

        print("3. Últimos 7 días")

        print("0. Volver")

        print("=" * 55)

        opcion = input("Seleccione una opción: ").strip()

        opciones = {
            "1": "-2d",
            "2": "-4d",
            "3": "-7d",
        }

        if opcion == "0":
            return None

        periodo = opciones.get(opcion)

        if periodo is None:

            print("Opción no válida.")

            continue

        return periodo


def ejecutar_intermitencias() -> dict[
    str,
    Any,
]:

    periodo = seleccionar_periodo_intermitencias()

    if periodo is None:

        return {
            "consulta": "intermitencias",
            "cancelado": True,
            "mensaje": ("Consulta cancelada " "por el usuario"),
        }

    return obtener_intermitencias(periodo)


# ============================================================
# MAIN
# ============================================================


def main() -> int:

    opciones: dict[
        str,
        Callable[
            [],
            dict[str, Any],
        ],
    ] = {
        "1": obtener_saturacion,
        "2": ejecutar_caidas,
        "3": obtener_crc,
        "4": obtener_correlacion,
        "5": ejecutar_intermitencias,
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

            resultado = servicio()

            if resultado.get("cancelado"):
                continue

            imprimir_resultado(resultado)

        except Exception as exc:

            print(
                f"Error: {exc}",
                file=sys.stderr,
            )


if __name__ == "__main__":
    raise SystemExit(main())
