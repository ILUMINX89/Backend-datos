"""Rutas HTTP de intermitencias HFC."""

from fastapi import APIRouter

from microservicios.cmts.intermitencias.service import obtener_intermitencias_actuales

router = APIRouter(tags=["CMTS - Intermitencias"])


@router.get("/intermitencias/actual")
def intermitencias_actual() -> dict:
    return {"ok": True, "data": obtener_intermitencias_actuales()}
