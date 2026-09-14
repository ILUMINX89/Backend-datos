from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from . import alarmas_service
from .models import ApiResponse, ErrorResponse, ReconocerAlarmaRequest

app = FastAPI(title="NOC BOA - Alarmas", version="0.1.0")


@app.exception_handler(Exception)
async def error_no_controlado(_request, _exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"ok": False, "error": "Error interno del servicio"})


@app.exception_handler(HTTPException)
async def error_http(_request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"ok": False, "error": str(exc.detail)})


@app.exception_handler(RequestValidationError)
async def error_validacion(_request: Request, _exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"ok": False, "error": "Parametros invalidos"})


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "alarmas"}


@app.get("/alarmas", response_model=ApiResponse)
def listar_alarmas(
    tipo: int | None = Query(default=None, ge=1, le=3),
    estado: str | None = Query(default=None, max_length=30),
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=100, ge=1, le=1000),
) -> ApiResponse:
    return ApiResponse(data=alarmas_service.obtener_alarmas(
        tipo=tipo, estado=estado, q=q, limit=limit
    ))


@app.get("/alarmas/resumen", response_model=ApiResponse)
def resumen() -> ApiResponse:
    return ApiResponse(data=alarmas_service.obtener_resumen())


@app.get("/alarmas/tendencia", response_model=ApiResponse)
def tendencia(horas: int = Query(default=24, ge=1, le=168)) -> ApiResponse:
    return ApiResponse(data=alarmas_service.obtener_tendencia(horas))


@app.get("/alarmas/top", response_model=ApiResponse)
def top(limit: int = Query(default=5, ge=1, le=100)) -> ApiResponse:
    return ApiResponse(data=alarmas_service.obtener_top(limit))


@app.get("/alarmas/{alarma_id}", response_model=ApiResponse,
         responses={404: {"model": ErrorResponse}})
def detalle(alarma_id: str) -> ApiResponse:
    alarma = alarmas_service.obtener_detalle(alarma_id)
    if not alarma:
        raise HTTPException(status_code=404, detail="Alarma no encontrada")
    return ApiResponse(data=alarma)


@app.post("/alarmas/{alarma_id}/reconocer", response_model=ApiResponse,
          responses={404: {"model": ErrorResponse}})
def reconocer(alarma_id: str, body: ReconocerAlarmaRequest) -> ApiResponse:
    alarma = alarmas_service.reconocer_alarma(alarma_id, body.usuario)
    if not alarma:
        raise HTTPException(status_code=404, detail="Alarma no encontrada")
    return ApiResponse(data=alarma)
