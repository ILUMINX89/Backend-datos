from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class Alarma(BaseModel):
    id: str
    fecha_hora: datetime
    tipo: Literal[1, 2, 3]
    estado: str
    olt: str
    puerto: str = ""
    descripcion: str
    sitio: str = ""
    valor: Any = None
    reconocida_por: str | None = None


class ReconocerAlarmaRequest(BaseModel):
    usuario: str = Field(min_length=1, max_length=100)


class ApiResponse(BaseModel):
    ok: bool = True
    data: Any = None


class ErrorResponse(BaseModel):
    ok: bool = False
    error: str
