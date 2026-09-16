"""Rutas HTTP de pérdida y latencia OLT."""

from fastapi import APIRouter, HTTPException, Query

from microservicios.olt.perdida_latencia.service import (
    obtener_latencia_equipo,
    obtener_perdida_latencia_actual,
)

router = APIRouter(tags=["OLT - Pérdida y latencia"])


@router.get("/perdida-latencia/actual")
def perdida_latencia_actual() -> dict:
    return {"ok": True, "data": obtener_perdida_latencia_actual()}


@router.get("/perdida-latencia/{equipo}")
def latencia_equipo(
    equipo: str,
    periodo: str = Query("-30d"),
) -> dict:
    try:
        data = obtener_latencia_equipo(equipo, periodo)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "data": data}
