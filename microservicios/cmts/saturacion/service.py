"""Logica de negocio para saturacion actual CMTS."""

from collections import defaultdict
from typing import Any

from microservicios.cmts.saturacion.queries import (
    obtener_bw_flux,
    obtener_snr_flux,
    obtener_utilizacion_flux,
)
from microservicios.influx import consultar_flux_temp

MUESTRAS_CONFIRMACION_SNR = 3
UMBRAL_UTILIZACION = 90.0

# Regla aislada para ajuste operacional:
# el bucket no define un umbral verificable.
UMBRAL_SNR_DEGRADADO_DB = 30.0


def _agrupar(
    filas: list[dict[str, Any]],
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    resultado: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)

    for fila in filas:
        cmts = fila.get("cmts")
        descripcion = fila.get("descripcion")

        if not cmts or not descripcion or fila.get("_value") is None:
            continue

        resultado[(str(cmts), str(descripcion))].append(fila)

    for muestras in resultado.values():
        muestras.sort(
            key=lambda fila: fila.get("_time"),
            reverse=True,
        )

    return dict(resultado)


def _porcentajes_utilizacion(
    filas_utilizacion: list[dict[str, Any]],
    bw: float,
) -> list[float]:
    porcentajes: list[float] = []

    for fila in filas_utilizacion:
        try:
            utilizacion = float(fila["_value"])
        except (KeyError, TypeError, ValueError):
            continue

        porcentaje = (utilizacion / bw) * 100.0

        # La ocupacion representa un porcentaje de capacidad,
        # por lo que nunca debe salir del rango 0-100.
        porcentaje = max(0.0, min(100.0, porcentaje))

        porcentajes.append(porcentaje)

    return porcentajes


def obtener_saturacion_actual() -> dict[str, Any]:
    muestras_bw = _agrupar(
        consultar_flux_temp(
            obtener_bw_flux(),
            fuente="cmts",
        )
    )

    muestras_utilizacion = _agrupar(
        consultar_flux_temp(
            obtener_utilizacion_flux(),
            fuente="cmts",
        )
    )

    muestras_snr = _agrupar(
        consultar_flux_temp(
            obtener_snr_flux(),
            fuente="cmts",
        )
    )

    resultado: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for (cmts, descripcion), filas_bw in muestras_bw.items():
        clave = (cmts, descripcion)

        filas_utilizacion = muestras_utilizacion.get(clave, [])

        if not filas_bw or not filas_utilizacion:
            continue

        try:
            bw_origen = filas_bw[0]["_value"]
            bw = float(bw_origen)
        except (KeyError, TypeError, ValueError):
            continue

        if bw <= 0:
            continue

        porcentajes = _porcentajes_utilizacion(
            filas_utilizacion,
            bw,
        )

        if not porcentajes:
            continue

        # Tomamos solamente las muestras cuya utilizacion sea
        # igual o superior al 90%.
        porcentajes_sobre_umbral = [
            valor for valor in porcentajes if valor >= UMBRAL_UTILIZACION
        ]

        # Cantidad de puntos >= 90%.
        # Esta es la principal medida de criticidad.
        puntos_sobre_umbral = len(porcentajes_sobre_umbral)

        # Promedio exclusivamente de los puntos >= 90%.
        promedio_sobre_umbral = (
            sum(porcentajes_sobre_umbral) / puntos_sobre_umbral
            if puntos_sobre_umbral
            else None
        )

        # Revisar las ultimas muestras de SNR.
        filas_ruido = muestras_snr.get(
            clave,
            [],
        )[:MUESTRAS_CONFIRMACION_SNR]

        valores_ruido: list[float] = []

        for fila in filas_ruido:
            try:
                valor_ruido = float(fila["_value"])
            except (KeyError, TypeError, ValueError):
                break

            if valor_ruido <= 0:
                break

            valores_ruido.append(valor_ruido)

        # Hay saturacion por uso si existe al menos
        # una muestra con utilizacion >= 90%.
        uso_confirmado = puntos_sobre_umbral > 0

        # Hay degradacion si las ultimas muestras de SNR
        # estan todas por debajo del umbral configurado.
        degradacion_confirmada = len(
            valores_ruido
        ) == MUESTRAS_CONFIRMACION_SNR and all(
            valor < UMBRAL_SNR_DEGRADADO_DB for valor in valores_ruido
        )

        if not uso_confirmado and not degradacion_confirmada:
            continue

        tipo = "degradacion" if degradacion_confirmada else "uso"

        estado = (
            "Saturación por degradación" if degradacion_confirmada else "Saturación"
        )

        # Para saturacion por uso mostramos el promedio
        # exclusivamente de los puntos >= 90%.
        #
        # Si el puerto entra solamente por degradacion SNR,
        # usamos el promedio completo de utilizacion.
        porcentaje_mostrado = (
            promedio_sobre_umbral
            if promedio_sobre_umbral is not None
            else sum(porcentajes) / len(porcentajes)
        )

        resultado[cmts].append(
            {
                "puerto": descripcion,
                "valor": round(porcentaje_mostrado, 2),
                "bw": bw_origen,
                "estado": estado,
                "tipo": tipo,
                "puntos_sobre_90": puntos_sobre_umbral,
                "muestras_analizadas": len(porcentajes),
                "ruido": (valores_ruido[0] if valores_ruido else None),
            }
        )

    def clave_criticidad(
        item: dict[str, Any],
    ) -> tuple[int, float]:
        """
        Orden de criticidad:

        1. Mayor cantidad de puntos >= 90%.
        2. En caso de empate, mayor porcentaje promedio.
        """
        return (
            int(item["puntos_sobre_90"]),
            float(item["valor"]),
        )

    datos: list[dict[str, Any]] = []

    # Ordenar los puertos dentro de cada CMTS.
    for cmts in resultado:
        puertos = sorted(
            resultado[cmts],
            key=clave_criticidad,
            reverse=True,
        )

        datos.append(
            {
                "cmts": cmts,
                "puertos": puertos,
            }
        )

    # Ordenar también los CMTS según su puerto más crítico.
    datos.sort(
        key=lambda grupo: clave_criticidad(grupo["puertos"][0]),
        reverse=True,
    )

    return {
        "datos": datos,
    }
