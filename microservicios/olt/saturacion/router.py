"""Rutas HTTP de saturacion OLT."""

from fastapi import APIRouter

from microservicios.olt.saturacion.service import obtener_saturacion

router = APIRouter(tags=["OLT - Saturación"])


@router.get("/saturacion")
def saturacion() -> dict:
    return {"ok": True, "data": obtener_saturacion()}
