"""Rutas HTTP de caídas e intermitencias OLT."""

from fastapi import APIRouter, Query

from microservicios.olt.caidas.service import (
    obtener_caidas,
    obtener_caidas_actuales,
    obtener_intermitencias,
)

router = APIRouter(
    tags=["OLT - Caídas"],
)


@router.get("/caidas")
def caidas(
    dias: int = Query(
        7,
        description=("Periodo histórico a consultar: " "2, 4 o 7 días"),
    ),
) -> dict:

    periodos = {
        2: "-2d",
        4: "-4d",
        7: "-7d",
    }

    periodo = periodos.get(dias)

    if periodo is None:
        return {
            "ok": False,
            "error": ("El parámetro dias solo " "puede ser 2, 4 o 7"),
        }

    return {
        "ok": True,
        "data": obtener_caidas(periodo),
    }


@router.get("/caidas/actuales")
def caidas_actuales() -> dict:

    return {
        "ok": True,
        "data": obtener_caidas_actuales(),
    }


@router.get("/intermitencias")
def intermitencias(
    dias: int = Query(
        7,
        description=("Periodo para detectar intermitencias: " "2, 4 o 7 días"),
    ),
) -> dict:

    periodos = {
        2: "-2d",
        4: "-4d",
        7: "-7d",
    }

    periodo = periodos.get(dias)

    if periodo is None:
        return {
            "ok": False,
            "error": ("El parámetro dias solo " "puede ser 2, 4 o 7"),
        }

    return {
        "ok": True,
        "data": obtener_intermitencias(periodo),
    }
