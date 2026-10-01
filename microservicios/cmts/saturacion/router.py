"""Rutas HTTP de saturacion CMTS basadas en cache."""

from datetime import datetime
from threading import Lock

from fastapi import APIRouter, BackgroundTasks

from microservicios.cmts.saturacion.cache import (
    guardar_estado,
    leer_estado,
    leer_saturacion,
)
from microservicios.cmts.saturacion.service import (
    actualizar_saturacion,
    iniciar_ejecucion_saturacion,
)

router = APIRouter(tags=["CMTS - Saturación"])
_actualizacion_lock = Lock()


def _ahora() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _ejecutar_actualizacion(estado_base: dict) -> None:
    try:
        actualizar_saturacion(estado_base)

    except Exception as exc:
        estado_actual = leer_estado()

        guardar_estado(
            {
                **estado_base,
                "estado": "error",
                "fase": "error",
                "bloque_actual": estado_actual.get("bloque_actual", 0),
                "porcentaje": estado_actual.get("porcentaje", 0.0),
                "ultimo_bloque_en": estado_actual.get("ultimo_bloque_en"),
                "finalizado_en": _ahora(),
                "error": str(exc),
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
        estado_base = iniciar_ejecucion_saturacion()
    except Exception:
        _actualizacion_lock.release()
        raise
    background_tasks.add_task(_ejecutar_actualizacion, estado_base)
    return {"ok": True, "estado": "procesando"}


@router.get("/saturacion/estado")
def saturacion_estado() -> dict:
    return {"ok": True, "data": leer_estado()}
