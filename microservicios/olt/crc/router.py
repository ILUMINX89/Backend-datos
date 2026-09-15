"""Rutas HTTP de errores CRC OLT."""

from fastapi import APIRouter

from microservicios.olt.crc.service import obtener_crc

router = APIRouter(tags=["OLT - CRC"])


@router.get("/crc")
def crc() -> dict:
    return {"ok": True, "data": obtener_crc()}
