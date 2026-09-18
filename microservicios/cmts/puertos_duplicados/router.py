"""Rutas HTTP de nodos asociados a multiples puertos CMTS."""

from fastapi import APIRouter

from microservicios.cmts.puertos_duplicados.service import (
    obtener_puertos_duplicados_actuales,
)

router = APIRouter(tags=["CMTS - Puertos duplicados"])


@router.get("/puertos-duplicados/actual")
def puertos_duplicados_actual() -> dict:
    return {"ok": True, "data": obtener_puertos_duplicados_actuales()}
