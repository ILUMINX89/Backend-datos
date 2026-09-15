"""Correlacion temporal de saturacion, CRC y caidas OLT."""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from microservicios.olt.caidas.service import obtener_caidas_por_puerto
from microservicios.olt.crc.service import obtener_episodios_crc
from microservicios.olt.saturacion.service import obtener_episodios_saturacion

MARGEN_CORRELACION_MINUTOS = 10


def eventos_se_relacionan(
    evento_a: dict[str, Any],
    evento_b: dict[str, Any],
    margen_minutos: int = MARGEN_CORRELACION_MINUTOS,
) -> bool:
    """Indica si dos intervalos se cruzan dentro del margen configurado."""
    ahora = datetime.now(timezone.utc)
    inicio_a = evento_a["inicio"].timestamp()
    fin_a = (evento_a.get("fin") or ahora).timestamp()
    inicio_b = evento_b["inicio"].timestamp()
    fin_b = (evento_b.get("fin") or ahora).timestamp()
    margen_segundos = margen_minutos * 60
    return inicio_b <= fin_a + margen_segundos and fin_b >= inicio_a - margen_segundos


def obtener_correlacion() -> dict[str, Any]:
    """Consulta cada fenomeno una vez y cruza sus episodios por OLT y puerto."""
    saturaciones = obtener_episodios_saturacion()
    crc = obtener_episodios_crc()
    caidas = obtener_caidas_por_puerto("-24h")

    claves = set(saturaciones) | set(crc) | set(caidas)
    resultado_olts: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for olt, puerto in claves:
        clave = (olt, puerto)
        eventos_sat = saturaciones.get(clave, [])
        eventos_crc = crc.get(clave, [])
        eventos_caida = caidas.get(clave, [])
        correlaciones: list[dict[str, Any]] = []

        for sat in eventos_sat:
            for evento_crc in eventos_crc:
                if eventos_se_relacionan(sat, evento_crc):
                    correlaciones.append(
                        {"tipo": "SATURACION + CRC", "saturacion": sat, "crc": evento_crc}
                    )

        for sat in eventos_sat:
            for caida in eventos_caida:
                if eventos_se_relacionan(sat, caida):
                    correlaciones.append(
                        {"tipo": "SATURACION + CAIDA", "saturacion": sat, "caida": caida}
                    )

        for evento_crc in eventos_crc:
            for caida in eventos_caida:
                if eventos_se_relacionan(evento_crc, caida):
                    correlaciones.append(
                        {"tipo": "CRC + CAIDA", "crc": evento_crc, "caida": caida}
                    )

        if not correlaciones:
            continue

        fenomenos = {
            fenomeno
            for correlacion in correlaciones
            for fenomeno in correlacion["tipo"].split(" + ")
        }
        diagnostico = " + ".join(
            fenomeno
            for fenomeno in ("SATURACION", "CRC", "CAIDA")
            if fenomeno in fenomenos
        )

        resultado_olts[olt].append(
            {
                "puerto": puerto,
                "diagnostico": diagnostico,
                "cantidad_correlaciones": len(correlaciones),
                "saturaciones": eventos_sat,
                "crc": eventos_crc,
                "caidas": eventos_caida,
                "correlaciones": correlaciones,
            }
        )

    datos = []
    for olt in sorted(resultado_olts):
        puertos = resultado_olts[olt]
        puertos.sort(key=lambda item: item["cantidad_correlaciones"], reverse=True)
        datos.append({"olt": olt, "cantidad_puertos": len(puertos), "puertos": puertos})

    return {
        "consulta": "correlacion_eventos",
        "periodo": "ultimas_24_horas",
        "margen_correlacion_minutos": MARGEN_CORRELACION_MINUTOS,
        "cantidad_olts": len(datos),
        "cantidad_puertos": sum(olt["cantidad_puertos"] for olt in datos),
        "datos": datos,
    }
