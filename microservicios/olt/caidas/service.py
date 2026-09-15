"""Lógica de negocio para caídas de puertos OLT por tráfico."""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from microservicios.influx import consultar_flux_temp
from microservicios.olt.caidas.queries import (
    obtener_caidas_actuales_flux,
    obtener_caidas_flux,
    obtener_ultima_actividad_flux,
)

MINIMO_MUESTRAS_CERO = 2


def _obtener_trafico(
    muestra: dict[str, Any],
) -> float | None:
    """
    Convierte el campo TRAFICO a float.
    """

    try:
        return float(muestra.get("TRAFICO"))

    except (
        TypeError,
        ValueError,
    ):
        return None


# ============================================================
# HISTÓRICO DE CAÍDAS
# ============================================================


def reconstruir_caidas(
    datos: list[dict[str, Any]],
    *,
    ahora: datetime | None = None,
) -> dict[
    tuple[str, str],
    list[dict[str, Any]],
]:
    """
    Reconstruye caídas históricas.

    Regla:

    tráfico > 0
    luego 0
    luego 0
    => caída confirmada

    Cuando vuelve tráfico > 0,
    la caída termina.
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

    for clave, muestras in muestras_por_puerto.items():

        muestras.sort(key=lambda fila: fila["_time"])

        ya_tuvo_trafico = False

        muestras_cero = 0

        inicio_posible_caida = None

        ultima_muestra_cero = None

        caida_confirmada = False

        trafico_antes_caida = None

        for muestra in muestras:

            fecha = muestra.get("_time")

            if fecha is None:
                continue

            trafico = _obtener_trafico(muestra)

            if trafico is None:
                continue

            # ==============================================
            # TIENE TRÁFICO
            # ==============================================

            if trafico > 0:

                if caida_confirmada and inicio_posible_caida is not None:
                    _agregar_caida(
                        resultado[clave],
                        inicio=inicio_posible_caida,
                        fin_calculo=fecha,
                        activa=False,
                        ultima_muestra_cero=ultima_muestra_cero,
                        trafico_antes_caida=trafico_antes_caida,
                        trafico_recuperacion=trafico,
                    )

                ya_tuvo_trafico = True

                trafico_antes_caida = trafico

                muestras_cero = 0

                inicio_posible_caida = None

                ultima_muestra_cero = None

                caida_confirmada = False

                continue

            # ==============================================
            # TRÁFICO EN CERO
            # ==============================================

            if not ya_tuvo_trafico:
                continue

            if muestras_cero == 0:
                inicio_posible_caida = fecha

            muestras_cero += 1

            ultima_muestra_cero = fecha

            if muestras_cero >= MINIMO_MUESTRAS_CERO:
                caida_confirmada = True

        # ==============================================
        # TERMINA EL RANGO Y SIGUE CAÍDO
        # ==============================================

        if caida_confirmada and inicio_posible_caida is not None:
            _agregar_caida(
                resultado[clave],
                inicio=inicio_posible_caida,
                fin_calculo=momento_actual,
                activa=True,
                ultima_muestra_cero=ultima_muestra_cero,
                trafico_antes_caida=trafico_antes_caida,
                trafico_recuperacion=None,
            )

    return dict(resultado)


def _agregar_caida(
    destino: list[dict[str, Any]],
    inicio: datetime,
    fin_calculo: datetime,
    *,
    activa: bool,
    ultima_muestra_cero: datetime | None = None,
    trafico_antes_caida: float | None = None,
    trafico_recuperacion: float | None = None,
) -> None:
    """
    Agrega una caída histórica.
    """

    duracion_minutos = (fin_calculo - inicio).total_seconds() / 60

    destino.append(
        {
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
            "ultima_muestra_cero": ultima_muestra_cero,
            "trafico_antes_caida_kbps": (
                round(
                    trafico_antes_caida,
                    2,
                )
                if trafico_antes_caida is not None
                else None
            ),
            "trafico_recuperacion_kbps": (
                round(
                    trafico_recuperacion,
                    2,
                )
                if trafico_recuperacion is not None
                else None
            ),
            "criterio": ("2_muestras_consecutivas_" "con_trafico_cero"),
        }
    )


def obtener_caidas_por_puerto(
    periodo: str = "-7d",
) -> dict[
    tuple[str, str],
    list[dict[str, Any]],
]:

    datos = consultar_flux_temp(obtener_caidas_flux(periodo))

    return reconstruir_caidas(datos)


def analizar_caidas(
    caidas_por_puerto: dict[
        tuple[str, str],
        list[dict[str, Any]],
    ],
) -> list[dict[str, Any]]:
    """
    Muestra puertos que tengan:

    - 3 o más caídas
    O
    - alguna caída de 2 horas o más
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

    periodos = {
        "-24h": "ultimas_24_horas",
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


# ============================================================
# CAÍDAS ACTUALES
# ============================================================


def detectar_puertos_sin_trafico(
    datos: list[dict[str, Any]],
) -> dict[
    tuple[str, str],
    dict[str, Any],
]:
    """
    Identifica puertos que actualmente
    continúan sin tráfico.

    Se consideran confirmados si las dos
    últimas muestras tienen tráfico <= 0.

    Ya NO descartamos:

        0
        0
        0

    porque puede tratarse de un puerto que
    lleva horas o días caído.
    """

    muestras_por_puerto: dict[
        tuple[str, str],
        list[dict[str, Any]],
    ] = defaultdict(list)

    for fila in datos:

        olt = str(fila.get("OLT") or "")

        puerto = str(fila.get("PUERTO") or "")

        fecha = fila.get("_time")

        trafico = _obtener_trafico(fila)

        if not olt or not puerto or fecha is None or trafico is None:
            continue

        copia = dict(fila)

        copia["TRAFICO"] = trafico

        muestras_por_puerto[(olt, puerto)].append(copia)

    resultado = {}

    for clave, muestras in muestras_por_puerto.items():

        muestras.sort(key=lambda fila: fila["_time"])

        if len(muestras) < 2:
            continue

        anterior = muestras[-2]

        actual = muestras[-1]

        trafico_anterior = anterior["TRAFICO"]

        trafico_actual = actual["TRAFICO"]

        # Dos muestras consecutivas sin tráfico.
        if trafico_anterior <= 0 and trafico_actual <= 0:
            resultado[clave] = {
                "muestras": muestras[-3:],
                "ultima_muestra": actual["_time"],
                "trafico_actual": trafico_actual,
            }

    return resultado


def obtener_ultima_actividad(
    puertos: list[tuple[str, str]],
    periodo: str = "-7d",
) -> dict[
    tuple[str, str],
    dict[str, Any],
]:
    """
    Busca cuándo fue la última vez
    que cada puerto tuvo tráfico.
    """

    if not puertos:
        return {}

    registros = consultar_flux_temp(
        obtener_ultima_actividad_flux(
            puertos,
            periodo,
        )
    )

    resultado = {}

    for fila in registros:

        olt = str(fila.get("OLT") or "")

        puerto = str(fila.get("PUERTO") or "")

        fecha = fila.get("_time")

        trafico = _obtener_trafico(fila)

        if not olt or not puerto or fecha is None:
            continue

        resultado[(olt, puerto)] = {
            "fecha": fecha,
            "trafico_kbps": trafico,
        }

    return resultado


def obtener_caidas_actuales() -> dict[
    str,
    Any,
]:
    """
    Obtiene los puertos actualmente
    sin tráfico y busca la última vez
    que tuvieron tráfico positivo.
    """

    # --------------------------------------------------------
    # PASO 1:
    # Últimas muestras
    # --------------------------------------------------------

    datos_actuales = consultar_flux_temp(obtener_caidas_actuales_flux())

    puertos_caidos = detectar_puertos_sin_trafico(datos_actuales)

    if not puertos_caidos:
        return {
            "consulta": "caidas_actuales_por_trafico",
            "criterio": ("2_ultimas_muestras_" "con_trafico_cero"),
            "cantidad_olts": 0,
            "cantidad_puertos": 0,
            "datos": [],
        }

    # --------------------------------------------------------
    # PASO 2:
    # Buscar última actividad únicamente
    # para los puertos actualmente caídos.
    # --------------------------------------------------------

    ultima_actividad = obtener_ultima_actividad(
        list(puertos_caidos.keys()),
        periodo="-7d",
    )

    ahora = datetime.now(timezone.utc)

    resultado_olts: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    # --------------------------------------------------------
    # PASO 3:
    # Construir resultado.
    # --------------------------------------------------------

    for (
        olt,
        puerto,
    ), info_actual in puertos_caidos.items():

        actividad = ultima_actividad.get((olt, puerto))

        ultima_vez_con_trafico = None

        ultimo_trafico = None

        minutos_sin_trafico = None

        horas_sin_trafico = None

        dias_sin_trafico = None

        if actividad is not None:

            ultima_vez_con_trafico = actividad.get("fecha")

            ultimo_trafico = actividad.get("trafico_kbps")

            if ultima_vez_con_trafico is not None:

                diferencia = ahora - ultima_vez_con_trafico

                minutos_sin_trafico = diferencia.total_seconds() / 60

                horas_sin_trafico = minutos_sin_trafico / 60

                dias_sin_trafico = horas_sin_trafico / 24

        muestras_salida = []

        for muestra in info_actual["muestras"]:

            trafico = _obtener_trafico(muestra)

            muestras_salida.append(
                {
                    "fecha": muestra.get("_time"),
                    "trafico_kbps": (
                        round(
                            trafico,
                            2,
                        )
                        if trafico is not None
                        else None
                    ),
                }
            )

        resultado_olts[olt].append(
            {
                "puerto": puerto,
                "estado": "CAIDO_ACTUAL",
                "confirmado": True,
                "trafico_actual_kbps": round(
                    info_actual["trafico_actual"],
                    2,
                ),
                "ultima_muestra": info_actual["ultima_muestra"],
                "ultima_vez_con_trafico": ultima_vez_con_trafico,
                "ultimo_trafico_kbps": (
                    round(
                        ultimo_trafico,
                        2,
                    )
                    if ultimo_trafico is not None
                    else None
                ),
                "tiempo_sin_trafico_minutos": (
                    round(
                        minutos_sin_trafico,
                        2,
                    )
                    if minutos_sin_trafico is not None
                    else None
                ),
                "tiempo_sin_trafico_horas": (
                    round(
                        horas_sin_trafico,
                        2,
                    )
                    if horas_sin_trafico is not None
                    else None
                ),
                "tiempo_sin_trafico_dias": (
                    round(
                        dias_sin_trafico,
                        2,
                    )
                    if dias_sin_trafico is not None
                    else None
                ),
                "historial_encontrado": actividad is not None,
                "muestras_actuales": muestras_salida,
            }
        )

    datos = []

    for olt in sorted(resultado_olts):

        puertos = resultado_olts[olt]

        puertos.sort(
            key=lambda item: (item["tiempo_sin_trafico_minutos"] or 0),
            reverse=True,
        )

        datos.append(
            {
                "olt": olt,
                "cantidad_puertos": len(puertos),
                "puertos": puertos,
            }
        )

    return {
        "consulta": "caidas_actuales_por_trafico",
        "criterio": ("2_ultimas_muestras_" "con_trafico_cero"),
        "busqueda_ultima_actividad": "ultimos_7_dias",
        "cantidad_olts": len(datos),
        "cantidad_puertos": sum(item["cantidad_puertos"] for item in datos),
        "datos": datos,
    }
