"""Rutas HTTP de temperatura OLT."""

from fastapi import APIRouter

from microservicios.olt.temperatura.service import obtener_temperatura_actual

router = APIRouter(tags=["OLT - Temperatura"])


@router.get("/temperatura/actual")
def temperatura_actual() -> dict:
    return {"ok": True, "data": obtener_temperatura_actual()}
