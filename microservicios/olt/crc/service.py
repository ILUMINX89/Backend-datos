"""Logica de negocio para episodios de errores CRC OLT."""

from collections import defaultdict
from typing import Any

from microservicios.influx import consultar_flux_temp
from microservicios.olt.crc.queries import obtener_crc_flux

SEPARACION_EPISODIO_MINUTOS = 30


def agrupar_episodios_crc(
    datos: list[dict[str, Any]],
) -> dict[tuple[str, str], list[dict[str, Any]]]:
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
            if not episodio:
                return
            try:
                valores = [float(item["CRC_POR_SEGUNDO"]) for item in episodio]
            except (KeyError, TypeError, ValueError):
                return
            inicio = episodio[0]["_time"]
            fin = episodio[-1]["_time"]
            resultado[clave].append(
                {
                    "inicio": inicio,
                    "fin": fin,
                    "muestras": len(episodio),
                    "duracion_entre_timestamps_minutos": round(
                        (fin - inicio).total_seconds() / 60, 2
                    ),
                    "maximo": round(max(valores), 2),
                    "promedio": round(sum(valores) / len(valores), 2),
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


def obtener_episodios_crc() -> dict[tuple[str, str], list[dict[str, Any]]]:
    datos = consultar_flux_temp(obtener_crc_flux())
    return agrupar_episodios_crc(datos)


def obtener_crc() -> dict[str, Any]:
    episodios = obtener_episodios_crc()
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
        "consulta": "errores_crc",
        "periodo": "ultimas_24_horas",
        "criterio": "mas_de_10_crc_por_segundo",
        "cantidad_olts": len(datos),
        "datos": datos,
    }
