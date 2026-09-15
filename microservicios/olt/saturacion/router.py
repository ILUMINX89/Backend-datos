"""Rutas HTTP de saturacion OLT."""

from fastapi import APIRouter

from microservicios.olt.saturacion.service import obtener_saturacion, obtener_saturacion_actual

router = APIRouter(tags=["OLT - Saturación"])


@router.get("/saturacion")
def saturacion() -> dict:
    return {"ok": True, "data": obtener_saturacion()}


@router.get("/saturacion/actual")
def saturacion_actual() -> dict:
    return {"ok": True, "data": obtener_saturacion_actual()}
