"""Logica de negocio para episodios de saturacion OLT."""

from collections import defaultdict
from typing import Any

from microservicios.influx import consultar_flux_temp
from microservicios.olt.saturacion.queries import obtener_saturacion_actual_flux, obtener_saturacion_flux

MINIMO_MUESTRAS = 2
SEPARACION_EPISODIO_MINUTOS = 30


def _clasificar_saturacion(maximo: float) -> int:
    if maximo >= 90:
        return 1
    if maximo >= 80:
        return 2
    return 3


def agrupar_episodios_saturacion(
    datos: list[dict[str, Any]],
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """Agrupa muestras consecutivas por OLT y puerto."""
    grupos: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for fila in datos:
        olt = str(fila.get("OLT") or "")
        puerto = str(fila.get("PUERTO") or "")
        if olt and puerto and fila.get("_time") is not None:
            grupos[(olt, puerto)].append(fila)

    resultado: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for clave, muestras in grupos.items():
        muestras.sort(key=lambda fila: fila["_time"])
        episodio: list[dict[str, Any]] = []

        def guardar() -> None:
            if len(episodio) < MINIMO_MUESTRAS:
                return
            try:
                valores = [float(item["SATURACION"]) for item in episodio]
            except (KeyError, TypeError, ValueError):
                return

            inicio = episodio[0]["_time"]
            fin = episodio[-1]["_time"]
            maximo = round(max(valores), 2)
            resultado[clave].append(
                {
                    "inicio": inicio,
                    "fin": fin,
                    "muestras": len(episodio),
                    "duracion_entre_timestamps_minutos": round(
                        (fin - inicio).total_seconds() / 60, 2
                    ),
                    "maximo": maximo,
                    "promedio": round(sum(valores) / len(valores), 2),
                    "tipo": _clasificar_saturacion(maximo),
                }
            )

        for muestra in muestras:
            if episodio:
                diferencia = (
                    muestra["_time"] - episodio[-1]["_time"]
                ).total_seconds() / 60
                if diferencia >= SEPARACION_EPISODIO_MINUTOS:
                    guardar()
                    episodio = []
            episodio.append(muestra)

        guardar()

    return dict(resultado)


def obtener_episodios_saturacion() -> dict[tuple[str, str], list[dict[str, Any]]]:
    datos = consultar_flux_temp(obtener_saturacion_flux())
    return agrupar_episodios_saturacion(datos)


def obtener_saturacion() -> dict[str, Any]:
    episodios = obtener_episodios_saturacion()
    resultado_olts: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for (olt, puerto), eventos in episodios.items():
        resultado_olts[olt].append(
            {
                "puerto": puerto,
                "cantidad_episodios": len(eventos),
                "episodios": eventos,
            }
        )

    datos = []
    for olt in sorted(resultado_olts):
        puertos = resultado_olts[olt]
        puertos.sort(
            key=lambda item: max(evento["maximo"] for evento in item["episodios"]),
            reverse=True,
        )
        datos.append({"olt": olt, "cantidad_puertos": len(puertos), "puertos": puertos})

    return {
        "consulta": "saturacion",
        "periodo": "ultimas_24_horas",
        "criterio": "saturacion_mayor_70_minimo_2_muestras",
        "separacion_nuevo_episodio_minutos": SEPARACION_EPISODIO_MINUTOS,
        "cantidad_olts": len(datos),
        "datos": datos,
    }


def obtener_saturacion_actual() -> dict[str, Any]:
    """Devuelve los puertos cuya ultima muestra supera el umbral actual."""
    filas = consultar_flux_temp(obtener_saturacion_actual_flux())
    resultado_olts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fila in filas:
        olt = str(fila.get("OLT") or "")
        puerto = str(fila.get("PUERTO") or "")
        if not olt or not puerto:
            continue
        resultado_olts[olt].append(
            {"puerto": puerto, "valor": round(float(fila["SATURACION"]), 2)}
        )
    return {
        "datos": [
            {"olt": olt, "puertos": sorted(resultado_olts[olt], key=lambda item: item["puerto"])}
            for olt in sorted(resultado_olts)
        ]
    }
