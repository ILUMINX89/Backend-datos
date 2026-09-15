"""Logica de negocio para caidas de puertos OLT."""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from microservicios.influx import consultar_flux_temp
from microservicios.olt.caidas.queries import obtener_caidas_flux

ESTADO_NORMAL = 6


def reconstruir_caidas(
    datos: list[dict[str, Any]],
    *,
    ahora: datetime | None = None,
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """Reconstruye los intervalos que empiezan con ESTADO != 6."""
    muestras_por_puerto: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for fila in datos:
        olt = str(fila.get("OLT") or "")
        puerto = str(fila.get("PUERTO") or "")
        if olt and puerto and fila.get("_time") is not None:
            muestras_por_puerto[(olt, puerto)].append(fila)

    momento_actual = ahora or datetime.now(timezone.utc)
    resultado: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for clave, muestras in muestras_por_puerto.items():
        muestras.sort(key=lambda fila: fila["_time"])
        inicio = None
        ultima_muestra_caida = None
        estado_detectado = None

        for muestra in muestras:
            try:
                estado = int(muestra.get("ESTADO"))
            except (TypeError, ValueError):
                continue
            fecha = muestra["_time"]

            if estado != ESTADO_NORMAL:
                if inicio is None:
                    inicio = fecha
                    estado_detectado = estado
                ultima_muestra_caida = fecha
                continue

            if inicio is not None:
                _agregar_caida(
                    resultado[clave], inicio, fecha, estado_detectado, activa=False
                )
                inicio = None
                ultima_muestra_caida = None
                estado_detectado = None

        if inicio is not None:
            _agregar_caida(
                resultado[clave],
                inicio,
                momento_actual,
                estado_detectado,
                activa=True,
                ultima_muestra_caida=ultima_muestra_caida,
            )

    return dict(resultado)


def _agregar_caida(
    destino: list[dict[str, Any]],
    inicio: datetime,
    fin_calculo: datetime,
    estado_detectado: int | None,
    *,
    activa: bool,
    ultima_muestra_caida: datetime | None = None,
) -> None:
    duracion_minutos = (fin_calculo - inicio).total_seconds() / 60
    caida = {
        "inicio": inicio,
        "fin": None if activa else fin_calculo,
        "duracion_minutos": round(duracion_minutos, 2),
        "duracion_horas": round(duracion_minutos / 60, 2),
        "dia": inicio.strftime("%Y-%m-%d"),
        "estado_detectado": estado_detectado,
        "mayor_2_horas": duracion_minutos >= 120,
        "activa": activa,
    }
    if activa:
        caida["ultima_muestra_caida"] = ultima_muestra_caida
    destino.append(caida)


def obtener_caidas_por_puerto(
    periodo: str = "-7d",
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    datos = consultar_flux_temp(obtener_caidas_flux(periodo))
    return reconstruir_caidas(datos)


def analizar_caidas(
    caidas_por_puerto: dict[tuple[str, str], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    resultado_olts: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for (olt, puerto), caidas in caidas_por_puerto.items():
        cantidad = len(caidas)
        mayores = [caida for caida in caidas if caida["mayor_2_horas"]]
        cumple_cantidad = cantidad >= 3
        cumple_duracion = bool(mayores)
        if not (cumple_cantidad or cumple_duracion):
            continue

        motivos = []
        if cumple_cantidad:
            motivos.append("3_o_mas_caidas")
        if cumple_duracion:
            motivos.append("caida_mayor_2_horas")
        tiempo_total = sum(caida["duracion_minutos"] for caida in caidas)

        resultado_olts[olt].append(
            {
                "puerto": puerto,
                "cantidad_caidas": cantidad,
                "caidas_mayores_2h": len(mayores),
                "cumple_por_cantidad": cumple_cantidad,
                "cumple_por_duracion": cumple_duracion,
                "motivos": motivos,
                "tiempo_total_caido_minutos": round(tiempo_total, 2),
                "tiempo_total_caido_horas": round(tiempo_total / 60, 2),
                "caidas": caidas,
            }
        )

    datos = []
    for olt in sorted(resultado_olts):
        puertos = resultado_olts[olt]
        puertos.sort(
            key=lambda item: (
                item["cantidad_caidas"],
                item["tiempo_total_caido_minutos"],
            ),
            reverse=True,
        )
        datos.append({"olt": olt, "cantidad_puertos": len(puertos), "puertos": puertos})
    return datos


def obtener_caidas() -> dict[str, Any]:
    datos = analizar_caidas(obtener_caidas_por_puerto())
    return {
        "consulta": "caidas_recurrentes",
        "periodo": "ultimos_7_dias",
        "criterio": "3_o_mas_caidas_o_caida_mayor_2_horas",
        "cantidad_olts": len(datos),
        "cantidad_puertos": sum(olt["cantidad_puertos"] for olt in datos),
        "datos": datos,
    }
