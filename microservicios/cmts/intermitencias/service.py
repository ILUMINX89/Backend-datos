"""Logica de negocio para intermitencias HFC."""

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

from microservicios.cmts.intermitencias.queries import (
    obtener_intermitencias_flux,
)
from microservicios.influx import consultar_flux_temp

MINIMO_MUESTRAS_CERO = 2
MINIMO_INTERMITENCIAS = 2


BLOQUES_7_DIAS = [
    ("-7d", "-6d"),
    ("-6d", "-5d"),
    ("-5d", "-4d"),
    ("-4d", "-3d"),
    ("-3d", "-2d"),
    ("-2d", "-1d"),
    ("-1d", None),
]


def _consultar_bloque(
    periodo: tuple[str, str | None],
) -> list[dict[str, Any]]:
    inicio, fin = periodo

    consulta = obtener_intermitencias_flux(
        inicio=inicio,
        fin=fin,
    )

    return consultar_flux_temp(
        consulta,
        fuente="cmts",
    )


def obtener_muestras_7_dias() -> list[dict[str, Any]]:
    """
    Consulta los 7 días en bloques diarios.

    Se ejecutan varios bloques en paralelo para evitar una única
    consulta pesada de 7 días.
    """

    filas: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        resultados = executor.map(
            _consultar_bloque,
            BLOQUES_7_DIAS,
        )

        for bloque in resultados:
            filas.extend(bloque)

    return filas


def _obtener_registrados(
    fila: dict[str, Any],
) -> float | None:
    try:
        return float(fila.get("_value"))

    except (
        TypeError,
        ValueError,
    ):
        return None


def reconstruir_caidas(
    filas: list[dict[str, Any]],
    *,
    ahora: datetime | None = None,
) -> dict[
    tuple[str, str, str],
    list[dict[str, Any]],
]:
    """
    Reconstruye caídas siguiendo el mismo criterio utilizado
    para OLT:

    - primero debe haber estado operativo;
    - 2 muestras consecutivas en cero confirman caída;
    - cuando vuelve a > 0 termina la caída;
    - todo el periodo continuo en cero cuenta como una sola caída.
    """

    muestras_por_puerto: dict[
        tuple[str, str, str],
        list[dict[str, Any]],
    ] = defaultdict(list)

    # ========================================================
    # AGRUPAR MUESTRAS
    # ========================================================

    for fila in filas:

        cmts = str(fila.get("cmts") or "").strip()

        puerto = str(fila.get("puerto") or "").strip()

        descripcion = str(fila.get("descripcion") or "").strip()

        fecha = fila.get("_time")

        registrados = _obtener_registrados(fila)

        if not cmts:
            continue

        if not puerto:
            continue

        if not descripcion:
            continue

        if fecha is None:
            continue

        if registrados is None:
            continue

        muestras_por_puerto[
            (
                cmts,
                puerto,
                descripcion,
            )
        ].append(fila)

    momento_actual = ahora or datetime.now(timezone.utc)

    resultado: dict[
        tuple[str, str, str],
        list[dict[str, Any]],
    ] = defaultdict(list)

    # ========================================================
    # RECONSTRUIR CAÍDAS
    # ========================================================

    for clave, muestras in muestras_por_puerto.items():

        muestras.sort(key=lambda fila: fila["_time"])

        ya_estuvo_operativo = False

        muestras_cero = 0

        inicio_posible_caida = None

        ultima_muestra_cero = None

        caida_confirmada = False

        registrados_antes_caida = None

        for muestra in muestras:

            fecha = muestra["_time"]

            registrados = _obtener_registrados(muestra)

            if registrados is None:
                continue

            # ================================================
            # OPERATIVO
            # ================================================

            if registrados > 0:

                if caida_confirmada and inicio_posible_caida is not None:
                    _agregar_caida(
                        resultado[clave],
                        inicio=inicio_posible_caida,
                        fin=fecha,
                        activa=False,
                        ultima_muestra_cero=(ultima_muestra_cero),
                        registrados_antes_caida=(registrados_antes_caida),
                        registrados_recuperacion=(registrados),
                    )

                ya_estuvo_operativo = True

                registrados_antes_caida = registrados

                muestras_cero = 0

                inicio_posible_caida = None

                ultima_muestra_cero = None

                caida_confirmada = False

                continue

            # ================================================
            # CERO
            # ================================================

            if not ya_estuvo_operativo:
                continue

            if muestras_cero == 0:
                inicio_posible_caida = fecha

            muestras_cero += 1

            ultima_muestra_cero = fecha

            if muestras_cero >= MINIMO_MUESTRAS_CERO:
                caida_confirmada = True

        # ====================================================
        # SIGUE CAÍDO AL FINAL DE LA VENTANA
        # ====================================================

        if caida_confirmada and inicio_posible_caida is not None:
            _agregar_caida(
                resultado[clave],
                inicio=inicio_posible_caida,
                fin=momento_actual,
                activa=True,
                ultima_muestra_cero=(ultima_muestra_cero),
                registrados_antes_caida=(registrados_antes_caida),
                registrados_recuperacion=None,
            )

    return dict(resultado)


def _agregar_caida(
    destino: list[dict[str, Any]],
    *,
    inicio: datetime,
    fin: datetime,
    activa: bool,
    ultima_muestra_cero: datetime | None,
    registrados_antes_caida: float | None,
    registrados_recuperacion: float | None,
) -> None:

    duracion_minutos = (fin - inicio).total_seconds() / 60

    destino.append(
        {
            "inicio": inicio,
            "fin": None if activa else fin,
            "activa": activa,
            "duracion_minutos": round(
                duracion_minutos,
                2,
            ),
            "duracion_horas": round(
                duracion_minutos / 60,
                2,
            ),
            "ultima_muestra_cero": (ultima_muestra_cero),
            "cm_registrados_antes_caida": (registrados_antes_caida),
            "cm_registrados_recuperacion": (registrados_recuperacion),
        }
    )


def analizar_intermitencias(
    caidas_por_puerto: dict[
        tuple[str, str, str],
        list[dict[str, Any]],
    ],
) -> list[dict[str, Any]]:

    resultado: list[dict[str, Any]] = []

    for (
        cmts,
        puerto,
        descripcion,
    ), caidas in caidas_por_puerto.items():

        cantidad = len(caidas)

        # Solo mostrar desde 2 intermitencias.
        if cantidad < MINIMO_INTERMITENCIAS:
            continue

        caidas_ordenadas = sorted(
            caidas,
            key=lambda item: item["inicio"],
            reverse=True,
        )

        tiempo_total = sum(
            float(
                item.get(
                    "duracion_minutos",
                    0,
                )
                or 0
            )
            for item in caidas
        )

        resultado.append(
            {
                "cmts": cmts,
                "puerto": puerto,
                "descripcion": descripcion,
                "estado": "INTERMITENTE",
                "cantidad_intermitencias": cantidad,
                "ultima_intermitencia": (caidas_ordenadas[0]["inicio"]),
                "tiempo_total_caido_minutos": round(
                    tiempo_total,
                    2,
                ),
                "intermitencias": caidas_ordenadas,
            }
        )

    resultado.sort(
        key=lambda item: (
            item["cantidad_intermitencias"],
            item["ultima_intermitencia"],
        ),
        reverse=True,
    )

    return resultado


def obtener_intermitencias_actuales() -> dict[str, Any]:

    filas = obtener_muestras_7_dias()

    caidas = reconstruir_caidas(filas)

    datos = analizar_intermitencias(caidas)

    return {
        "consulta": "intermitencias_hfc",
        "periodo": "ultimos_7_dias",
        "criterio_deteccion": ("2_muestras_consecutivas_" "con_cm_registrados_cero"),
        "criterio_reporte": ("2_o_mas_intermitencias_en_7_dias"),
        "minimo_intermitencias": (MINIMO_INTERMITENCIAS),
        "cantidad_puertos_intermitentes": len(datos),
        "datos": datos,
    }
