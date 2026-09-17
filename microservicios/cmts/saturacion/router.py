"""Rutas HTTP de saturacion CMTS."""

from fastapi import APIRouter

from microservicios.cmts.saturacion.service import obtener_saturacion_actual

router = APIRouter(tags=["CMTS - Saturación"])


@router.get("/saturacion/actual")
def saturacion_actual() -> dict:
    return {"ok": True, "data": obtener_saturacion_actual()}
