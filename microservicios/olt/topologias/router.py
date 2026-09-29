"""Endpoints HTTP de topologias OLT."""

import mimetypes
import posixpath
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

from microservicios.olt.topologias import service

router = APIRouter(prefix="/topologias", tags=["OLT - Topologias"])


def _respuesta_error(exc: service.TopologiasError) -> HTTPException:
    return HTTPException(status_code=exc.estado, detail=exc.mensaje)


@router.get("/health")
def health() -> dict:
    data = service.estado()
    listo = all(data[clave] for clave in ("ssh", "ruta", "data_dir", "temporales_dir", "imagenes_dir"))
    return {"ok": listo, "data": data}


@router.get("")
def menu() -> dict:
    nombres = {"huawei": "Huawei", "zte": "ZTE", "nokia": "Nokia", "onnet": "ONNET", "ftto": "FTTO"}
    return {"ok": True, "data": [{"id": clave, "nombre": nombres[clave]} for clave in service.CATEGORIAS]}


@router.get("/guardadas")
def guardadas() -> dict:
    try:
        return {"ok": True, "data": service.topologias_guardadas()}
    except service.TopologiasError as exc:
        raise _respuesta_error(exc) from exc


@router.get("/media/{archivo}")
def media(archivo: str) -> FileResponse:
    try:
        local = service.imagen_local(archivo)
        tipo = service.IMAGENES[local.suffix.lower()]
        return FileResponse(local, media_type=tipo, content_disposition_type="inline")
    except service.TopologiasError as exc:
        raise _respuesta_error(exc) from exc


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


def _transmitir(categoria: str, ruta: str) -> StreamingResponse:
    if categoria not in service.CATEGORIAS:
        raise HTTPException(status_code=400, detail="Categoria invalida")
    contexto = service.conexion()
    conectado = False
    try:
        _, sftp = contexto.__enter__()
        conectado = True
        origen, datos, extension = service.archivo_validado(sftp, categoria, ruta)
        archivo = sftp.open(origen, "rb")
    except service.TopologiasError as exc:
        if conectado:
            contexto.__exit__(type(exc), exc, exc.__traceback__)
        raise _respuesta_error(exc) from exc
    except OSError as exc:
        if conectado:
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
    tipo = service.IMAGENES.get(extension) or mimetypes.guess_type(nombre)[0] or "application/octet-stream"
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(nombre)}",
        "Content-Length": str(datos.st_size),
    }
    return StreamingResponse(bloques(), media_type=tipo, headers=headers)


@router.get("/{categoria}/imagen")
def imagen(categoria: str, ruta: str = Query(...)) -> FileResponse:
    if posixpath.splitext(ruta)[1].lower() not in service.IMAGENES:
        raise HTTPException(status_code=400, detail="Se requiere una imagen JPG o PNG")
    return _imagen_materializada(categoria, ruta)


@router.get("/{categoria}/archivo")
def archivo(categoria: str, ruta: str = Query(...)) -> StreamingResponse:
    return _transmitir(categoria, ruta)


@router.get("/{categoria}/jpg")
def jpg(categoria: str, ruta: str = Query(...)) -> FileResponse:
    if posixpath.splitext(ruta)[1].lower() not in service.VISIO:
        raise HTTPException(status_code=400, detail="Se requiere un archivo VSD o VSDX")
    return _imagen_materializada(categoria, ruta)


@router.get("/{categoria}/link")
def link(categoria: str, ruta: str = Query(...)) -> dict:
    try:
        return {"ok": True, "data": service.materializar_topologia(categoria, ruta)}
    except service.TopologiasError as exc:
        raise _respuesta_error(exc) from exc


def _imagen_materializada(categoria: str, ruta: str) -> FileResponse:
    try:
        data = service.materializar_topologia(categoria, ruta)
        local = service.imagen_local(posixpath.basename(data["enlace"]))
        return FileResponse(local, media_type=service.IMAGENES[local.suffix.lower()],
                            content_disposition_type="inline")
    except service.TopologiasError as exc:
        raise _respuesta_error(exc) from exc
