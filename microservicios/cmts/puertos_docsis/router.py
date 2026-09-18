"""Rutas HTTP de puertos DOCSIS."""

from fastapi import APIRouter

from microservicios.cmts.puertos_docsis.service import (
    obtener_puertos_docsis_actuales,
)

router = APIRouter(tags=["CMTS - Puertos DOCSIS"])


@router.get("/puertos-docsis/actual")
def puertos_docsis_actual() -> dict:
    return {"ok": True, "data": obtener_puertos_docsis_actuales()}
