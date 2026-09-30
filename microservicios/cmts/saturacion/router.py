"""Rutas HTTP de saturacion CMTS basadas en cache."""

from datetime import datetime
from threading import Lock

from fastapi import APIRouter, BackgroundTasks

from microservicios.cmts.saturacion.cache import (
    guardar_estado,
    leer_estado,
    leer_saturacion,
)
from microservicios.cmts.saturacion.service import TOTAL_BLOQUES, actualizar_saturacion

router = APIRouter(tags=["CMTS - Saturación"])
_actualizacion_lock = Lock()


def _ahora() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _ejecutar_actualizacion() -> None:
    try:
        actualizar_saturacion()

    except Exception as exc:
        estado_actual = leer_estado()

        guardar_estado(
            {
                **estado_actual,
                "estado": "error",
                "fase": "error",
                "finalizado_en": _ahora(),
                "error": str(exc),
            }
        )

    else:
        estado_actual = leer_estado()

        guardar_estado(
            {
                **estado_actual,
                "estado": "listo",
                "fase": "finalizado",
                "bloque_actual": TOTAL_BLOQUES,
                "bloques_totales": TOTAL_BLOQUES,
                "porcentaje": 100.0,
                "finalizado_en": _ahora(),
                "error": None,
            }
        )

    finally:
        _actualizacion_lock.release()


@router.get("/saturacion/actual")
def saturacion_actual() -> dict:
    return {"ok": True, "data": leer_saturacion()}


@router.post("/saturacion/actualizar")
def saturacion_actualizar(background_tasks: BackgroundTasks) -> dict:
    if not _actualizacion_lock.acquire(blocking=False):
        return {"ok": True, "estado": "procesando"}
    try:
        guardar_estado(
            {
                "estado": "procesando",
                "fase": "consultando_influx",
                "iniciado_en": _ahora(),
                "finalizado_en": None,
                "error": None,
                "bloque_actual": 0,
                "bloques_totales": TOTAL_BLOQUES,
                "porcentaje": 0.0,
                "ultimo_bloque_en": None,
            }
        )
    except Exception:
        _actualizacion_lock.release()
        raise
    background_tasks.add_task(_ejecutar_actualizacion)
    return {"ok": True, "estado": "procesando"}


@router.get("/saturacion/estado")
def saturacion_estado() -> dict:
    return {"ok": True, "data": leer_estado()}
