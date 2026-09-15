"""Lógica de negocio para caídas de puertos OLT por tráfico."""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from microservicios.influx import consultar_flux_temp
from microservicios.olt.caidas.queries import (
    obtener_caidas_flux,
    obtener_estado_actual_flux,
    obtener_ultima_actividad_flux,
    obtener_ultima_muestra_conocida_flux,
)

MINIMO_MUESTRAS_CERO = 2
MINUTOS_SIN_MUESTRAS = 15


def _obtener_trafico(
    muestra: dict[str, Any],
) -> float | None:
    try:
        return float(muestra.get("TRAFICO"))

    except (
        TypeError,
        ValueError,
    ):
        return None


# ============================================================
# HISTÓRICO
# ============================================================


def reconstruir_caidas(
    datos: list[dict[str, Any]],
    *,
    ahora: datetime | None = None,
) -> dict[
    tuple[str, str],
    list[dict[str, Any]],
]:
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

            trafico = _obtener_trafico(muestra)

            if fecha is None or trafico is None:
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
# INTERMITENCIAS
# ============================================================


def obtener_intermitencias(
    periodo: str = "-7d",
) -> dict[str, Any]:
    """
    Detecta puertos intermitentes reutilizando
    las mismas caídas históricas.

    Regla:

    Si un OLT + PUERTO presenta más de
    2 caídas dentro del mismo día:

        3 o más caídas

    se considera INTERMITENTE.
    """

    periodos = {
        "-2d": "ultimos_2_dias",
        "-4d": "ultimos_4_dias",
        "-7d": "ultimos_7_dias",
    }

    if periodo not in periodos:
        raise ValueError(
            "Periodo de intermitencias no permitido. " "Use -2d, -4d o -7d."
        )

    # Reutilizamos la consulta y reconstrucción
    # que ya usa el módulo de caídas.
    caidas_por_puerto = obtener_caidas_por_puerto(periodo)

    resultado_olts: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    for (
        olt,
        puerto,
    ), caidas in caidas_por_puerto.items():

        caidas_por_dia: dict[
            str,
            list[dict[str, Any]],
        ] = defaultdict(list)

        # ==========================================
        # AGRUPAR CAÍDAS POR DÍA
        # ==========================================

        for caida in caidas:

            inicio = caida.get("inicio")

            if inicio is None:
                continue

            dia = inicio.strftime("%Y-%m-%d")

            caidas_por_dia[dia].append(caida)

        dias_intermitentes = []

        # ==========================================
        # VALIDAR MÁS DE 2 CAÍDAS EN EL MISMO DÍA
        # ==========================================

        for (
            dia,
            eventos,
        ) in caidas_por_dia.items():

            cantidad_caidas = len(eventos)

            if cantidad_caidas <= 2:
                continue

            tiempo_total_minutos = sum(
                evento.get(
                    "duracion_minutos",
                    0,
                )
                for evento in eventos
            )

            eventos_ordenados = sorted(
                eventos,
                key=lambda evento: evento.get("inicio"),
            )

            dias_intermitentes.append(
                {
                    "dia": dia,
                    "estado": "INTERMITENTE",
                    "cantidad_caidas": cantidad_caidas,
                    "tiempo_total_caido_minutos": round(
                        tiempo_total_minutos,
                        2,
                    ),
                    "tiempo_total_caido_horas": round(
                        tiempo_total_minutos / 60,
                        2,
                    ),
                    "eventos": eventos_ordenados,
                }
            )

        if not dias_intermitentes:
            continue

        dias_intermitentes.sort(
            key=lambda item: item["dia"],
            reverse=True,
        )

        total_caidas = sum(dia["cantidad_caidas"] for dia in dias_intermitentes)

        maximo_caidas_dia = max(dia["cantidad_caidas"] for dia in dias_intermitentes)

        resultado_olts[olt].append(
            {
                "puerto": puerto,
                "estado": "INTERMITENTE",
                "cantidad_dias_intermitentes": len(dias_intermitentes),
                "total_caidas_en_dias_intermitentes": total_caidas,
                "maximo_caidas_en_un_dia": maximo_caidas_dia,
                "dias": dias_intermitentes,
            }
        )

    datos = []

    for olt in sorted(resultado_olts):

        puertos = resultado_olts[olt]

        puertos.sort(
            key=lambda item: (
                item["maximo_caidas_en_un_dia"],
                item["cantidad_dias_intermitentes"],
            ),
            reverse=True,
        )

        datos.append(
            {
                "olt": olt,
                "cantidad_puertos_intermitentes": len(puertos),
                "puertos": puertos,
            }
        )

    return {
        "consulta": "intermitencias_por_caidas",
        "periodo": periodos[periodo],
        "criterio": "mas_de_2_caidas_en_un_mismo_dia",
        "minimo_caidas_para_intermitencia": 3,
        "cantidad_olts": len(datos),
        "cantidad_puertos_intermitentes": sum(
            olt["cantidad_puertos_intermitentes"] for olt in datos
        ),
        "datos": datos,
    }


# ============================================================
# ACTUALES
# ============================================================


def _agrupar_muestras_recientes(
    datos: list[dict[str, Any]],
) -> dict[
    tuple[str, str],
    list[dict[str, Any]],
]:

    resultado: dict[
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

        resultado[(olt, puerto)].append(copia)

    for muestras in resultado.values():
        muestras.sort(key=lambda fila: fila["_time"])

    return dict(resultado)


def _indexar_ultima_muestra(
    datos: list[dict[str, Any]],
) -> dict[
    tuple[str, str],
    dict[str, Any],
]:

    resultado = {}

    for fila in datos:

        olt = str(fila.get("OLT") or "")

        puerto = str(fila.get("PUERTO") or "")

        fecha = fila.get("_time")

        trafico = _obtener_trafico(fila)

        if not olt or not puerto or fecha is None or trafico is None:
            continue

        resultado[(olt, puerto)] = {
            "fecha": fecha,
            "trafico": trafico,
        }

    return resultado


def _buscar_ultima_actividad(
    puertos: list[tuple[str, str]],
) -> dict[
    tuple[str, str],
    dict[str, Any],
]:

    if not puertos:
        return {}

    datos = consultar_flux_temp(
        obtener_ultima_actividad_flux(
            puertos,
            "-7d",
        )
    )

    resultado = {}

    for fila in datos:

        olt = str(fila.get("OLT") or "")

        puerto = str(fila.get("PUERTO") or "")

        fecha = fila.get("_time")

        trafico = _obtener_trafico(fila)

        if not olt or not puerto or fecha is None:
            continue

        resultado[(olt, puerto)] = {
            "fecha": fecha,
            "trafico": trafico,
        }

    return resultado


def obtener_caidas_actuales() -> dict[
    str,
    Any,
]:
    """
    Detecta tres escenarios:

    1. CAIDO_ACTUAL:
       las dos últimas muestras están en 0.

    2. SIN_MUESTRAS_RECIENTES:
       el puerto tenía tráfico o al menos una muestra histórica,
       pero lleva más de 15 minutos sin reportar.

    3. CAIDO_SIN_FECHA:
       está actualmente en 0 pero no encontramos
       tráfico positivo en los últimos 7 días.
    """

    ahora = datetime.now(timezone.utc)

    # --------------------------------------------------------
    # MUESTRAS DE LOS ÚLTIMOS 30 MINUTOS
    # --------------------------------------------------------

    recientes = consultar_flux_temp(obtener_estado_actual_flux())

    recientes_por_puerto = _agrupar_muestras_recientes(recientes)

    # --------------------------------------------------------
    # ÚLTIMA MUESTRA CONOCIDA EN 7 DÍAS
    # --------------------------------------------------------

    ultima_muestra_datos = consultar_flux_temp(
        obtener_ultima_muestra_conocida_flux("-7d")
    )

    ultima_muestra_por_puerto = _indexar_ultima_muestra(ultima_muestra_datos)

    candidatos: dict[
        tuple[str, str],
        dict[str, Any],
    ] = {}

    # --------------------------------------------------------
    # CASO 1:
    # TIENE MUESTRAS RECIENTES Y DOS ÚLTIMAS SON 0
    # --------------------------------------------------------

    for (
        clave,
        muestras,
    ) in recientes_por_puerto.items():

        if len(muestras) < 2:
            continue

        anterior = muestras[-2]

        actual = muestras[-1]

        trafico_anterior = anterior["TRAFICO"]

        trafico_actual = actual["TRAFICO"]

        if trafico_anterior <= 0 and trafico_actual <= 0:
            candidatos[clave] = {
                "estado_base": "CAIDO_ACTUAL",
                "ultima_muestra": actual["_time"],
                "trafico_actual": trafico_actual,
                "muestras": muestras[-3:],
            }

    # --------------------------------------------------------
    # CASO 2:
    # DEJÓ DE REPORTAR COMPLETAMENTE
    # --------------------------------------------------------

    for (
        clave,
        info,
    ) in ultima_muestra_por_puerto.items():

        if clave in recientes_por_puerto:
            continue

        fecha = info["fecha"]

        minutos_sin_muestras = (ahora - fecha).total_seconds() / 60

        if minutos_sin_muestras >= MINUTOS_SIN_MUESTRAS:
            candidatos[clave] = {
                "estado_base": "SIN_MUESTRAS_RECIENTES",
                "ultima_muestra": fecha,
                "trafico_actual": None,
                "muestras": [],
            }

    if not candidatos:
        return {
            "consulta": "caidas_actuales_por_trafico",
            "cantidad_olts": 0,
            "cantidad_puertos": 0,
            "datos": [],
        }

    # --------------------------------------------------------
    # BUSCAR ÚLTIMA VEZ CON TRÁFICO
    # --------------------------------------------------------

    ultima_actividad = _buscar_ultima_actividad(list(candidatos.keys()))

    resultado_olts: dict[
        str,
        list[dict[str, Any]],
    ] = defaultdict(list)

    for (
        olt,
        puerto,
    ), info in candidatos.items():

        actividad = ultima_actividad.get((olt, puerto))

        estado = info["estado_base"]

        ultima_vez_con_trafico = None
        ultimo_trafico = None
        minutos_sin_trafico = None
        horas_sin_trafico = None
        dias_sin_trafico = None

        if actividad is not None:

            ultima_vez_con_trafico = actividad["fecha"]

            ultimo_trafico = actividad["trafico"]

            diferencia = ahora - ultima_vez_con_trafico

            minutos_sin_trafico = diferencia.total_seconds() / 60

            horas_sin_trafico = minutos_sin_trafico / 60

            dias_sin_trafico = horas_sin_trafico / 24

        elif estado == "CAIDO_ACTUAL":

            estado = "CAIDO_SIN_FECHA"

        muestras_salida = []

        for muestra in info["muestras"]:

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
                "estado": estado,
                "ultima_muestra": info["ultima_muestra"],
                "trafico_actual_kbps": (
                    round(
                        info["trafico_actual"],
                        2,
                    )
                    if info["trafico_actual"] is not None
                    else None
                ),
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
        "criterios": {
            "caido_actual": ("2_ultimas_muestras_" "con_trafico_cero"),
            "sin_muestras_recientes": (
                f"mas_de_" f"{MINUTOS_SIN_MUESTRAS}_" "minutos_sin_reportar"
            ),
            "busqueda_ultima_actividad": "ultimos_7_dias",
        },
        "cantidad_olts": len(datos),
        "cantidad_puertos": sum(item["cantidad_puertos"] for item in datos),
        "datos": datos,
    }
