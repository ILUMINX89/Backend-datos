"""Rutas HTTP de recursos ZTE."""

from fastapi import APIRouter

from microservicios.olt.recursos_zte.service import obtener_licencias_bajas

router = APIRouter(tags=["OLT - Recursos ZTE"])


@router.get("/recursos-zte/licencias-bajas")
def licencias_bajas() -> dict:
    return {"ok": True, "data": obtener_licencias_bajas()}
