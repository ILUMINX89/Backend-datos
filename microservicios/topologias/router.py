"""Rutas HTTP para consultar topologias de OLT por SSH/SFTP."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from microservicios.topologias.service import (
    diagnostico_topologias,
    iterar_archivo,
    iterar_jpg_convertido,
    listar_topologias,
    menu_topologias,
)

router = APIRouter(prefix="/topologias", tags=["Topologias"])


def _respuesta_error(exc: Exception) -> HTTPException:
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, RuntimeError):
        return HTTPException(status_code=503, detail=str(exc))
    return HTTPException(status_code=500, detail="Error interno de topologias")


def _listar(categoria: str, buscar: str, limite: int) -> dict:
    try:
        return {
            "ok": True,
            "data": listar_topologias(
                categoria=categoria,
                buscar=buscar,
                limite=limite,
            ),
        }
    except Exception as exc:
        raise _respuesta_error(exc) from exc


@router.get("/health")
def health_topologias() -> dict:
    try:
        return {"ok": True, "data": diagnostico_topologias()}
    except Exception as exc:
        raise _respuesta_error(exc) from exc


@router.get("/olts")
def menu_olts() -> dict:
    return {"ok": True, "data": menu_topologias()}


@router.get("/olts/huawei")
def topologias_huawei(
    buscar: str = Query(default="", max_length=200),
    limite: int = Query(default=200, ge=1, le=1000),
) -> dict:
    return _listar("huawei", buscar, limite)


@router.get("/olts/zte")
def topologias_zte(
    buscar: str = Query(default="", max_length=200),
    limite: int = Query(default=200, ge=1, le=1000),
) -> dict:
    return _listar("zte", buscar, limite)


@router.get("/olts/nokia")
def topologias_nokia(
    buscar: str = Query(default="", max_length=200),
    limite: int = Query(default=200, ge=1, le=1000),
) -> dict:
    return _listar("nokia", buscar, limite)


@router.get("/olts/onnet")
def topologias_onnet(
    buscar: str = Query(default="", max_length=200),
    limite: int = Query(default=200, ge=1, le=1000),
) -> dict:
    return _listar("onnet", buscar, limite)


@router.get("/olts/ftto")
def topologias_ftto(
    buscar: str = Query(default="", max_length=200),
    limite: int = Query(default=200, ge=1, le=1000),
) -> dict:
    return _listar("ftto", buscar, limite)


@router.get("/olts/{categoria}/archivo")
def descargar_archivo(
    categoria: str,
    ruta: str = Query(min_length=1, max_length=1000),
) -> StreamingResponse:
    try:
        contenido, meta = iterar_archivo(categoria, ruta)
    except Exception as exc:
        raise _respuesta_error(exc) from exc

    nombre = quote(str(meta["nombre"]))
    return StreamingResponse(
        contenido,
        media_type=str(meta["media_type"]),
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{nombre}",
            "Content-Length": str(meta["tamano_bytes"]),
        },
    )


@router.get("/olts/{categoria}/imagen")
def ver_imagen(
    categoria: str,
    ruta: str = Query(min_length=1, max_length=1000),
) -> StreamingResponse:
    try:
        contenido, meta = iterar_archivo(
            categoria,
            ruta,
            solo_imagen=True,
        )
    except Exception as exc:
        raise _respuesta_error(exc) from exc

    nombre = quote(str(meta["nombre"]))
    return StreamingResponse(
        contenido,
        media_type=str(meta["media_type"]),
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{nombre}",
            "Content-Length": str(meta["tamano_bytes"]),
        },
    )


@router.get("/olts/{categoria}/jpg")
def convertir_y_ver_jpg(
    categoria: str,
    ruta: str = Query(min_length=1, max_length=1000),
) -> StreamingResponse:
    try:
        contenido, meta = iterar_jpg_convertido(categoria, ruta)
    except Exception as exc:
        raise _respuesta_error(exc) from exc

    nombre = quote(str(meta["nombre"]))
    return StreamingResponse(
        contenido,
        media_type="image/jpeg",
        headers={
            "Content-Disposition": f"inline; filename*=UTF-8''{nombre}",
            "Content-Length": str(meta["tamano_bytes"]),
            "X-Topologias-Cache": (
                "HIT" if meta["desde_cache"] else "MISS"
            ),
        },
    )
