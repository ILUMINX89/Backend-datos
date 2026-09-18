"""Aplicacion FastAPI principal de Backend Datos."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from microservicios.alarmas.app import router as alarmas_router
from microservicios.cmts.saturacion.router import router as cmts_saturacion_router
from microservicios.cmts.intermitencias.router import (
    router as cmts_intermitencias_router,
)
from microservicios.cmts.puertos_docsis.router import (
    router as cmts_puertos_docsis_router,
)
from microservicios.olt.caidas.router import router as caidas_router
from microservicios.olt.correlacion.router import router as correlacion_router
from microservicios.olt.crc.router import router as crc_router
from microservicios.olt.perdida_latencia.router import (
    router as perdida_latencia_router,
)
from microservicios.olt.saturacion.router import router as saturacion_router
from microservicios.olt.temperatura.router import router as temperatura_router

app = FastAPI(title="Backend Datos API", version="1.0.0")


@app.exception_handler(Exception)
async def error_no_controlado(_request: Request, _exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"ok": False, "error": "Error interno del servicio"},
    )


@app.exception_handler(HTTPException)
async def error_http(_request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"ok": False, "error": str(exc.detail)},
    )


@app.exception_handler(RequestValidationError)
async def error_validacion(
    _request: Request, _exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"ok": False, "error": "Parametros invalidos"},
    )


@app.get("/health")
def health() -> dict[str, object]:
    return {"ok": True, "service": "Backend Datos API"}


app.include_router(saturacion_router, prefix="/api/olt")
app.include_router(caidas_router, prefix="/api/olt")
app.include_router(crc_router, prefix="/api/olt")
app.include_router(correlacion_router, prefix="/api/olt")
app.include_router(temperatura_router, prefix="/api/olt")
app.include_router(perdida_latencia_router, prefix="/api/olt")
app.include_router(cmts_saturacion_router, prefix="/api/cmts")
app.include_router(cmts_puertos_docsis_router, prefix="/api/cmts")
app.include_router(cmts_intermitencias_router, prefix="/api/cmts")

# Las rutas existentes se conservan mientras el frontend PHP migra al nuevo servicio.
app.include_router(alarmas_router)
