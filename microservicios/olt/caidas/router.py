"""Rutas HTTP de caidas OLT."""

from fastapi import APIRouter

from microservicios.olt.caidas.service import obtener_caidas

router = APIRouter(tags=["OLT - Caídas"])


@router.get("/caidas")
def caidas() -> dict:
    return {"ok": True, "data": obtener_caidas()}
