"""Lógica de negocio para intermitencias HFC."""

from typing import Any

from microservicios.cmts.intermitencias.queries import (
    obtener_intermitencias_flux,
)
from microservicios.influx import consultar_flux_temp

MINIMO_INTERMITENCIAS = 2


def _numero_entero(
    valor: Any,
    default: int = 0,
) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return default


def procesar_intermitencias(
    filas: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Normaliza los resultados ya resumidos por InfluxDB.

    Influx solamente devuelve puertos que tuvieron
    2 o más eventos confirmados.
    """

    resultado: list[dict[str, Any]] = []

    for fila in filas:
        cmts = str(fila.get("cmts") or "").strip()
        puerto = str(fila.get("puerto") or "").strip()
        descripcion = str(fila.get("descripcion") or "").strip()

        cantidad = _numero_entero(fila.get("cantidad_intermitencias"))

        if not cmts:
            continue

        if not puerto:
            continue

        if not descripcion:
            continue

        if cantidad < MINIMO_INTERMITENCIAS:
            continue

        resultado.append(
            {
                "cmts": cmts,
                "puerto": puerto,
                "descripcion": descripcion,
                "cantidad_intermitencias": cantidad,
            }
        )

    resultado.sort(
        key=lambda item: (
            -item["cantidad_intermitencias"],
            item["cmts"],
            item["puerto"],
        )
    )

    return resultado


def obtener_intermitencias_actuales(
    periodo: str = "-1h",
) -> dict[str, Any]:
    """
    Consulta intermitencias HFC.

    Durante pruebas usamos solamente -1h.

    NO se usan consultas paralelas.
    NO se descargan siete días crudos a Python.
    El conteo de eventos ocurre dentro de InfluxDB.
    """

    consulta = obtener_intermitencias_flux(periodo)

    filas = consultar_flux_temp(
        consulta,
        fuente="cmts",
    )

    datos = procesar_intermitencias(filas)

    periodos = {
        "-1h": "ultima_hora",
        "-24h": "ultimas_24_horas",
        "-7d": "ultimos_7_dias",
    }

    return {
        "consulta": "intermitencias_hfc",
        "periodo": periodos.get(periodo, periodo),
        "campo": "cm_registrados",
        "criterio_caida": ("2_muestras_consecutivas_con_cm_registrados_en_0"),
        "criterio_intermitencia": ("2_o_mas_caidas_en_el_periodo"),
        "minimo_intermitencias": MINIMO_INTERMITENCIAS,
        "cantidad_puertos_intermitentes": len(datos),
        "datos": datos,
    }
