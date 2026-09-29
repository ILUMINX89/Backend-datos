"""Rutas HTTP de pérdida y latencia OLT."""

from fastapi import APIRouter

from microservicios.olt.perdida_latencia.service import (
    obtener_perdida_latencia_actual,
)

router = APIRouter(tags=["OLT - Pérdida y latencia"])


@router.get("/perdida-latencia/actual")
def perdida_latencia_actual() -> dict:
    return {"ok": True, "data": obtener_perdida_latencia_actual()}
