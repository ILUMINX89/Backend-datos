"""Logica de negocio para nodos asociados a multiples puertos CMTS."""

from typing import Any

from microservicios.cmts.puertos_duplicados.queries import (
    obtener_puertos_duplicados_flux,
)
from microservicios.influx import consultar_flux_temp


def normalizar_descripcion(descripcion: Any) -> str:
    """Replica la normalizacion validada en ``probar_cmts.py``."""
    if descripcion is None:
        return ""

    return " ".join(str(descripcion).strip().upper().split())


def procesar_puertos_duplicados(
    filas: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Agrupa nodos y conserva solamente ubicaciones CMTS/puerto distintas."""
    nodos: dict[str, set[tuple[str, str]]] = {}

    for fila in filas:
        nodo = normalizar_descripcion(fila.get("descripcion"))

        if not nodo.startswith("NODO "):
            continue

        cmts = str(fila.get("cmts") or "SIN_CMTS").strip()
        puerto = str(fila.get("puerto") or "SIN_PUERTO").strip()

        nodos.setdefault(nodo, set()).add((cmts, puerto))

    resultado = [
        {
            "nodo": nodo,
            "cantidad_ubicaciones": len(ubicaciones),
            "ubicaciones": [
                {"cmts": cmts, "puerto": puerto}
                for cmts, puerto in sorted(ubicaciones)
            ],
        }
        for nodo, ubicaciones in nodos.items()
        if len(ubicaciones) > 1
    ]

    resultado.sort(
        key=lambda item: (-item["cantidad_ubicaciones"], item["nodo"])
    )
    return resultado


def obtener_puertos_duplicados_actuales() -> dict[str, Any]:
    consulta = obtener_puertos_duplicados_flux()
    filas = consultar_flux_temp(consulta, fuente="cmts")
    datos = procesar_puertos_duplicados(filas)

    return {
        "cantidad_nodos_duplicados": len(datos),
        "datos": datos,
    }
