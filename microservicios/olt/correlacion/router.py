"""Rutas HTTP de correlacion OLT."""

from fastapi import APIRouter

from microservicios.olt.correlacion.service import obtener_correlacion

router = APIRouter(tags=["OLT - Correlación"])


@router.get("/correlacion")
def correlacion() -> dict:
    return {"ok": True, "data": obtener_correlacion()}
