"""Lógica de negocio del dominio de alarmas."""

from collections import Counter
from datetime import datetime, timezone

from microservicios.influx import consultar_flux_temp

from .models import Alarma
from .queries import (
    obtener_alarmas_flux,
    obtener_saturacion_flux,
)


def clasificar_alarma_por_estado(estado_equipo) -> int:
    """
    Clasificación provisional.

    Por ahora solo sabemos que:
    ESTADO == 6 -> normal
    ESTADO != 6 -> anomalía

    Hasta conocer qué significa cada código de ESTADO,
    toda anomalía se considera Tipo 1.
    """
    del estado_equipo
    return 1


def fila_a_alarma(row: dict) -> Alarma:
    """
    Convierte una fila devuelta por InfluxDB
    en el modelo normalizado Alarma.
    """

    olt = str(row.get("OLT") or "")
    puerto = str(row.get("PUERTO") or "")

    descripcion = str(row.get("DESCRIPCION") or "").strip()

    estado_equipo = row.get("ESTADO")
    tx = row.get("TX")
    rx = row.get("RX")

    # El pivot puede conservar alguno de estos campos.
    fecha_hora = row.get("_time") or row.get("_stop") or datetime.now(timezone.utc)

    if not descripcion:
        descripcion = f"Estado anómalo detectado en " f"{olt} puerto {puerto}"

    tipo = clasificar_alarma_por_estado(estado_equipo)

    # ID estable para que el frontend pueda reconocer
    # que sigue siendo la misma alarma entre cada polling.
    alarma_id = f"estado-puerto:" f"{olt}:" f"{puerto}:" f"{estado_equipo}"

    valor = {
        "estado_equipo": estado_equipo,
        "tx": tx,
        "rx": rx,
    }

    return Alarma(
        id=alarma_id,
        fecha_hora=fecha_hora,
        tipo=tipo,
        estado="ACTIVA",
        olt=olt,
        puerto=puerto,
        descripcion=descripcion,
        sitio="",
        valor=valor,
    )


def fila_saturacion_a_alarma(row: dict) -> Alarma:
    olt = str(row.get("OLT") or "")
    puerto = str(row.get("PUERTO") or "")

    saturacion = float(row.get("SATURACION") or 0)

    input_kbps = row.get("INPUT")
    output_kbps = row.get("OUTPUT")

    fecha_hora = row.get("_time") or row.get("_stop") or datetime.now(timezone.utc)

    # ==========================================
    # Clasificación por porcentaje
    # ==========================================

    if saturacion >= 90:
        tipo = 1
    elif saturacion >= 80:
        tipo = 2
    else:
        tipo = 3

    alarma_id = f"saturacion:{olt}:{puerto}"

    return Alarma(
        id=alarma_id,
        fecha_hora=fecha_hora,
        tipo=tipo,
        estado="ACTIVA",
        olt=olt,
        puerto=puerto,
        descripcion=(
            f"Puerto alcanzó {saturacion:.2f}% "
            f"de utilización en las últimas 24 horas"
        ),
        sitio="",
        valor={
            "saturacion": round(
                saturacion,
                2,
            ),
            "input_kbps": input_kbps,
            "output_kbps": output_kbps,
        },
    )


def obtener_alarmas(
    *,
    tipo: int | None = None,
    estado: str | None = None,
    q: str | None = None,
    limit: int = 100,
) -> list[Alarma]:
    """
    Obtiene alarmas reales desde InfluxDB.

    Incluye:
    - Tipo 1: ESTADO != 6
    - Tipo 2: Saturación > 25% en las últimas 24 horas
    """

    flux = obtener_alarmas_flux(
        tipo=tipo,
        estado=estado,
        limit=limit,
    )

    rows = consultar_flux_temp(flux)

    alarmas = [fila_a_alarma(row) for row in rows]

    flux_saturacion = obtener_saturacion_flux()

    rows_saturacion = consultar_flux_temp(flux_saturacion)

    alarmas_saturacion = [fila_saturacion_a_alarma(row) for row in rows_saturacion]

    alarmas.extend(alarmas_saturacion)

    if tipo is not None:
        alarmas = [alarma for alarma in alarmas if alarma.tipo == tipo]

    if estado:
        alarmas = [
            alarma for alarma in alarmas if alarma.estado.upper() == estado.upper()
        ]

    if q:
        termino = q.casefold()

        alarmas = [
            alarma
            for alarma in alarmas
            if termino
            in " ".join(
                [
                    alarma.id,
                    alarma.olt,
                    alarma.puerto,
                    alarma.descripcion,
                    alarma.sitio,
                ]
            ).casefold()
        ]

    alarmas_tipo2 = [alarma for alarma in alarmas if alarma.tipo == 2]

    otras_alarmas = [alarma for alarma in alarmas if alarma.tipo != 2]

    alarmas_tipo2.sort(
        key=lambda alarma: alarma.fecha_hora,
        reverse=True,
    )

    otras_alarmas.sort(
        key=lambda alarma: alarma.fecha_hora,
        reverse=True,
    )

    resultado = alarmas_tipo2.copy()

    espacio_restante = max(
        limit - len(resultado),
        0,
    )

    resultado.extend(otras_alarmas[:espacio_restante])

    return resultado[:limit]


def obtener_resumen() -> dict[str, int]:
    alarmas = obtener_alarmas(limit=1000)

    conteo = Counter(alarma.tipo for alarma in alarmas if alarma.estado == "ACTIVA")

    return {
        "total": sum(conteo.values()),
        "tipo1": conteo[1],
        "tipo2": conteo[2],
        "tipo3": conteo[3],
    }


def obtener_tendencia(
    horas: int,
) -> list[dict[str, int | str]]:
    """
    Temporal.

    Todavía no implementamos la consulta histórica real.
    """
    del horas
    return []


def obtener_top(
    limit: int,
) -> list[dict[str, int | str]]:
    """
    Calcula el top usando las alarmas actuales.
    Más adelante podremos hacerlo directamente en Flux.
    """

    alarmas = obtener_alarmas(limit=1000)

    conteo = Counter(alarma.olt for alarma in alarmas)

    return [
        {
            "equipo": equipo,
            "total": total,
        }
        for equipo, total in conteo.most_common(limit)
    ]


def obtener_detalle(
    alarma_id: str,
) -> Alarma | None:
    alarmas = obtener_alarmas(limit=1000)

    return next(
        (alarma for alarma in alarmas if alarma.id == alarma_id),
        None,
    )


def reconocer_alarma(
    alarma_id: str,
    usuario: str,
) -> Alarma | None:
    """
    Por ahora el reconocimiento vive en memoria
    solamente durante la respuesta actual.

    Más adelante definiremos dónde persistirlo.
    """

    alarma = obtener_detalle(alarma_id)

    if alarma:
        alarma.reconocida_por = usuario

    return alarma
