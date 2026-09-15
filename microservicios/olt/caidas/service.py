"""Lógica de negocio para caídas de puertos OLT por tráfico."""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from microservicios.influx import consultar_flux_temp
from microservicios.olt.caidas.queries import obtener_caidas_flux

MINIMO_MUESTRAS_CERO = 2


def reconstruir_caidas(
    datos: list[dict[str, Any]],
    *,
    ahora: datetime | None = None,
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """
    Reconstruye caídas usando tráfico real.

    Regla:
    - El puerto debe haber tenido tráfico > 0 previamente.
    - Si luego tiene 2 muestras consecutivas con TRAFICO == 0,
      se confirma la caída.
    - La caída comienza en la primera muestra en 0.
    - Cuando TRAFICO vuelve a ser > 0, termina la caída.
    - Si termina el periodo y sigue en 0, la caída queda activa.
    """

    muestras_por_puerto: dict[
        tuple[str, str],
        list[dict[str, Any]],
    ] = defaultdict(list)

    for fila in datos:
        olt = str(fila.get("OLT") or "")

        puerto = str(fila.get("PUERTO") or "")

        fecha = fila.get("_time")

        if olt and puerto and fecha is not None:
            muestras_por_puerto[(olt, puerto)].append(fila)

    momento_actual = ahora or datetime.now(timezone.utc)

    resultado: dict[
        tuple[str, str],
        list[dict[str, Any]],
    ] = defaultdict(list)

    for (
        olt,
        puerto,
    ), muestras in muestras_por_puerto.items():

        muestras.sort(key=lambda fila: fila["_time"])

        # El puerto debe haber tenido tráfico
        # antes de poder declararse caído.
        ya_tuvo_trafico = False

        # Contador de muestras consecutivas en 0.
        muestras_cero = 0

        # Primera muestra que cayó a 0.
        inicio_posible_caida = None

        # Caída ya confirmada.
        caida_confirmada = False

        # Última muestra recibida en cero.
        ultima_muestra_cero = None

        for muestra in muestras:

            fecha = muestra.get("_time")

            trafico = muestra.get("TRAFICO")

            if fecha is None:
                continue

            try:
                trafico = float(trafico)

            except (
                TypeError,
                ValueError,
            ):
                continue

            # ==================================
            # HAY TRÁFICO
            # ==================================

            if trafico > 0:

                ya_tuvo_trafico = True

                # Si había una caída confirmada,
                # el tráfico vuelve y la cerramos.
                if caida_confirmada:

                    _agregar_caida(
                        resultado[(olt, puerto)],
                        inicio_posible_caida,
                        fecha,
                        activa=False,
                    )

                # Reiniciar estado.
                muestras_cero = 0
                inicio_posible_caida = None
                caida_confirmada = False
                ultima_muestra_cero = None

                continue

            # ==================================
            # TRÁFICO EN CERO
            # ==================================

            # Si nunca tuvo tráfico anteriormente,
            # no asumimos que es una caída nueva.
            if not ya_tuvo_trafico:
                continue

            # Primera muestra en cero.
            if muestras_cero == 0:

                inicio_posible_caida = fecha

            muestras_cero += 1

            ultima_muestra_cero = fecha

            # Al llegar a 2 muestras consecutivas
            # confirmamos la caída.
            if muestras_cero >= MINIMO_MUESTRAS_CERO:

                caida_confirmada = True

        # ======================================
        # SI TERMINÓ EL HISTÓRICO Y SIGUE CAÍDO
        # ======================================

        if caida_confirmada and inicio_posible_caida is not None:

            _agregar_caida(
                resultado[(olt, puerto)],
                inicio_posible_caida,
                momento_actual,
                activa=True,
                ultima_muestra_cero=ultima_muestra_cero,
            )

    return dict(resultado)


def _agregar_caida(
    destino: list[dict[str, Any]],
    inicio: datetime,
    fin_calculo: datetime,
    *,
    activa: bool,
    ultima_muestra_cero: datetime | None = None,
) -> None:
    """
    Agrega una caída al resultado.
    """

    duracion_minutos = (fin_calculo - inicio).total_seconds() / 60

    caida = {
        "inicio": inicio,
        "fin": None if activa else fin_calculo,
        "duracion_minutos": round(
            duracion_minutos,
            2,
        ),
        "duracion_horas": round(
            duracion_minutos / 60,
            2,
        ),
        "dia": inicio.strftime("%Y-%m-%d"),
        "mayor_2_horas": duracion_minutos >= 120,
        "activa": activa,
        "criterio": "2_muestras_consecutivas_trafico_cero",
    }

    if activa:
        caida["ultima_muestra_cero"] = ultima_muestra_cero

    destino.append(caida)


def obtener_caidas_por_puerto(
    periodo: str = "-7d",
) -> dict[
    tuple[str, str],
    list[dict[str, Any]],
]:
    """
    Consulta Influx y reconstruye
    las caídas por OLT + PUERTO.
    """

    datos = consultar_flux_temp(obtener_caidas_flux(periodo))

    return reconstruir_caidas(datos)


def analizar_caidas(
    caidas_por_puerto: dict[
        tuple[str, str],
        list[dict[str, Any]],
    ],
) -> list[dict[str, Any]]:
    """
    Incluye puertos que cumplan:

    - 3 o más caídas en 7 días
    O
    - al menos una caída de 2 horas o más
    """

    resultado_olts: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    for (
        olt,
        puerto,
    ), caidas in caidas_por_puerto.items():

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
                "tiempo_total_caido_minutos": round(
                    tiempo_total,
                    2,
                ),
                "tiempo_total_caido_horas": round(
                    tiempo_total / 60,
                    2,
                ),
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

        datos.append(
            {
                "olt": olt,
                "cantidad_puertos": len(puertos),
                "puertos": puertos,
            }
        )

    return datos


def obtener_caidas(
    periodo: str = "-7d",
) -> dict[str, Any]:
    """
    Resultado final de caídas.
    """
    periodos = {
        "-2d": "ultimos_2_dias",
        "-4d": "ultimos_4_dias",
        "-7d": "ultimos_7_dias",
    }

    datos = analizar_caidas(obtener_caidas_por_puerto(periodo))

    return {
        "consulta": "caidas_por_trafico",
        "periodo": periodos.get(
            periodo,
            periodo,
        ),
        "criterio_deteccion": ("2_muestras_consecutivas_" "con_trafico_cero"),
        "criterio_reporte": ("3_o_mas_caidas_" "o_caida_mayor_2_horas"),
        "cantidad_olts": len(datos),
        "cantidad_puertos": sum(olt["cantidad_puertos"] for olt in datos),
        "datos": datos,
    }

def obtener_caidas_actuales() -> dict[str, Any]:
    
    def analizar_caidas_actuales(
    datos: list[dict[str, Any]],
) -> list[dict[str, Any]]: