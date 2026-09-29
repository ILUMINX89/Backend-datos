"""Endpoints HTTP de topologias OLT."""

import mimetypes
import posixpath
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from microservicios.olt.topologias import service

router = APIRouter(prefix="/topologias", tags=["OLT - Topologias"])


def _respuesta_error(exc: service.TopologiasError) -> HTTPException:
    return HTTPException(status_code=exc.estado, detail=exc.mensaje)


@router.get("/health")
def health() -> dict:
    try:
        data = service.estado()
        return {"ok": data["ruta"], "data": data}
    except service.TopologiasError as exc:
        raise _respuesta_error(exc) from exc


@router.get("")
def menu() -> dict:
    nombres = {"huawei": "Huawei", "zte": "ZTE", "nokia": "Nokia", "onnet": "ONNET", "ftto": "FTTO"}
    return {"ok": True, "data": [{"id": clave, "nombre": nombres[clave]} for clave in service.CATEGORIAS]}


def _buscar(categoria: str, buscar: str, limite: int) -> dict:
    try:
        return {"ok": True, "data": service.buscar(categoria, buscar, limite)}
    except service.TopologiasError as exc:
        raise _respuesta_error(exc) from exc


@router.get("/huawei")
def huawei(buscar: str = "", limite: int = Query(200, ge=1, le=1000)) -> dict:
    return _buscar("huawei", buscar, limite)


@router.get("/zte")
def zte(buscar: str = "", limite: int = Query(200, ge=1, le=1000)) -> dict:
    return _buscar("zte", buscar, limite)


@router.get("/nokia")
def nokia(buscar: str = "", limite: int = Query(200, ge=1, le=1000)) -> dict:
    return _buscar("nokia", buscar, limite)


@router.get("/onnet")
def onnet(buscar: str = "", limite: int = Query(200, ge=1, le=1000)) -> dict:
    return _buscar("onnet", buscar, limite)


@router.get("/ftto")
def ftto(buscar: str = "", limite: int = Query(200, ge=1, le=1000)) -> dict:
    return _buscar("ftto", buscar, limite)


def _transmitir(categoria: str, ruta: str, modo: str) -> StreamingResponse:
    if categoria not in service.CATEGORIAS:
        raise HTTPException(status_code=400, detail="Categoria invalida")
    contexto = service.conexion()
    try:
        ssh, sftp = contexto.__enter__()
        origen, datos, extension = service.archivo_validado(sftp, categoria, ruta)
        if modo == "imagen" and extension not in service.IMAGENES:
            raise service.TopologiasError("Se requiere una imagen JPG o PNG", 400)
        if modo == "jpg":
            origen = service.jpg_cacheado(ssh, sftp, categoria, ruta)
            extension = ".jpg"
            datos = sftp.stat(origen)
        archivo = sftp.open(origen, "rb")
    except service.TopologiasError as exc:
        contexto.__exit__(type(exc), exc, exc.__traceback__)
        raise _respuesta_error(exc) from exc
    except OSError as exc:
        contexto.__exit__(type(exc), exc, exc.__traceback__)
        raise HTTPException(status_code=404, detail="Archivo no encontrado") from exc

    def bloques():
        try:
            while bloque := archivo.read(64 * 1024):
                yield bloque
        finally:
            archivo.close()
            contexto.__exit__(None, None, None)

    nombre = posixpath.basename(ruta)
    if modo == "jpg":
        nombre = posixpath.splitext(nombre)[0] + ".jpg"
    tipo = service.IMAGENES.get(extension) or mimetypes.guess_type(nombre)[0] or "application/octet-stream"
    disposicion = "inline" if modo != "archivo" else "attachment"
    headers = {
        "Content-Disposition": f"{disposicion}; filename*=UTF-8''{quote(nombre)}",
        "Content-Length": str(datos.st_size),
    }
    return StreamingResponse(bloques(), media_type=tipo, headers=headers)


@router.get("/{categoria}/imagen")
def imagen(categoria: str, ruta: str = Query(...)) -> StreamingResponse:
    return _transmitir(categoria, ruta, "imagen")


@router.get("/{categoria}/archivo")
def archivo(categoria: str, ruta: str = Query(...)) -> StreamingResponse:
    return _transmitir(categoria, ruta, "archivo")


@router.get("/{categoria}/jpg")
def jpg(categoria: str, ruta: str = Query(...)) -> StreamingResponse:
    return _transmitir(categoria, ruta, "jpg")
