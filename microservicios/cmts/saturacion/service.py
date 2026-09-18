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
UMBRAL_UTILIZACION = 80.0
# Regla aislada para ajuste operacional: el bucket no define un umbral verificable.
UMBRAL_SNR_DEGRADADO_DB = 30.0


def _agrupar(filas: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    resultado: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for fila in filas:
        cmts = fila.get("cmts")
        descripcion = fila.get("descripcion")
        if not cmts or not descripcion or fila.get("_value") is None:
            continue
        resultado[(str(cmts), str(descripcion))].append(fila)
    for muestras in resultado.values():
        muestras.sort(key=lambda fila: fila.get("_time"), reverse=True)
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

        # El porcentaje mostrado y usado para el analisis HFC representa
        # ocupacion de capacidad, por lo que nunca debe salir del rango 0-100.
        porcentaje = max(0.0, min(100.0, porcentaje))
        porcentajes.append(porcentaje)

    return porcentajes


def obtener_saturacion_actual() -> dict[str, Any]:
    muestras_bw = _agrupar(consultar_flux_temp(obtener_bw_flux(), fuente="cmts"))
    muestras_utilizacion = _agrupar(
        consultar_flux_temp(obtener_utilizacion_flux(), fuente="cmts")
    )
    muestras_snr = _agrupar(consultar_flux_temp(obtener_snr_flux(), fuente="cmts"))
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

        porcentajes = _porcentajes_utilizacion(filas_utilizacion, bw)
        if not porcentajes:
            continue

        porcentajes_sobre_80 = [
            valor for valor in porcentajes if valor > UMBRAL_UTILIZACION
        ]
        puntos_sobre_80 = len(porcentajes_sobre_80)
        promedio_sobre_80 = (
            sum(porcentajes_sobre_80) / puntos_sobre_80
            if puntos_sobre_80
            else None
        )

        filas_ruido = muestras_snr.get(clave, [])[:MUESTRAS_CONFIRMACION_SNR]
        valores_ruido: list[float] = []
        for fila in filas_ruido:
            try:
                valor_ruido = float(fila["_value"])
            except (KeyError, TypeError, ValueError):
                break
            if valor_ruido <= 0:
                break
            valores_ruido.append(valor_ruido)

        uso_confirmado = puntos_sobre_80 > 0
        degradacion_confirmada = (
            len(valores_ruido) == MUESTRAS_CONFIRMACION_SNR
            and all(valor < UMBRAL_SNR_DEGRADADO_DB for valor in valores_ruido)
        )
        if not uso_confirmado and not degradacion_confirmada:
            continue

        tipo = "degradacion" if degradacion_confirmada else "uso"
        estado = "Saturación por degradación" if degradacion_confirmada else "Saturación"

        # Para saturacion por uso mostramos el promedio de los puntos >80.
        # Si el puerto entra solo por degradacion SNR, usamos el promedio
        # de utilizacion de la ventana, igualmente limitado a 0-100.
        porcentaje_mostrado = (
            promedio_sobre_80
            if promedio_sobre_80 is not None
            else sum(porcentajes) / len(porcentajes)
        )

        resultado[cmts].append(
            {
                "puerto": descripcion,
                "valor": round(porcentaje_mostrado, 2),
                "bw": bw_origen,
                "estado": estado,
                "tipo": tipo,
                "puntos_sobre_80": puntos_sobre_80,
                "muestras_analizadas": len(porcentajes),
                "ruido": valores_ruido[0] if valores_ruido else None,
            }
        )

    def clave_criticidad(item: dict[str, Any]) -> tuple[int, float]:
        return (int(item["puntos_sobre_80"]), float(item["valor"]))

    datos: list[dict[str, Any]] = []
    for cmts in resultado:
        puertos = sorted(resultado[cmts], key=clave_criticidad, reverse=True)
        datos.append({"cmts": cmts, "puertos": puertos})

    datos.sort(
        key=lambda grupo: clave_criticidad(grupo["puertos"][0]),
        reverse=True,
    )
    return {"datos": datos}
