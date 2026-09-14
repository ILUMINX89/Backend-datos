"""Logica de negocio de alarmas.

MOCK temporal: reemplazar `_alarmas` por llamadas a `queries.py` cuando se
documente el esquema real de InfluxDB.
"""

from collections import Counter
from datetime import datetime, timedelta, timezone

from .models import Alarma


def clasificar_alarma(tipo: int) -> str:
    return {1: "Critica", 2: "Mayor", 3: "Menor"}.get(tipo, "Desconocida")


_ahora = datetime.now(timezone.utc)
_alarmas: list[Alarma] = [
    Alarma(id="mock-1", fecha_hora=_ahora - timedelta(minutes=3), tipo=1,
           estado="ACTIVA", olt="OLT-DEMO-01", puerto="1/1/3",
           descripcion="MOCK: equipo sin respuesta", sitio="Sitio demo", valor=None),
    Alarma(id="mock-2", fecha_hora=_ahora - timedelta(minutes=18), tipo=2,
           estado="ACTIVA", olt="OLT-DEMO-02", puerto="1/0/3",
           descripcion="MOCK: alta tasa de errores", sitio="Sitio demo", valor="15.8 %"),
    Alarma(id="mock-3", fecha_hora=_ahora - timedelta(minutes=31), tipo=3,
           estado="ACTIVA", olt="OLT-DEMO-03", puerto="1/1/5",
           descripcion="MOCK: temperatura alta", sitio="Sitio demo", valor="70 C"),
]


def obtener_alarmas(
    *, tipo: int | None = None, estado: str | None = None,
    q: str | None = None, limit: int = 100,
) -> list[Alarma]:
    resultado = _alarmas
    if tipo is not None:
        resultado = [alarma for alarma in resultado if alarma.tipo == tipo]
    if estado:
        resultado = [alarma for alarma in resultado if alarma.estado.upper() == estado.upper()]
    if q:
        termino = q.casefold()
        resultado = [alarma for alarma in resultado if termino in " ".join([
            alarma.id, alarma.olt, alarma.puerto, alarma.descripcion, alarma.sitio
        ]).casefold()]
    return resultado[:limit]


def obtener_resumen() -> dict[str, int]:
    conteo = Counter(alarma.tipo for alarma in _alarmas if alarma.estado == "ACTIVA")
    return {"total": sum(conteo.values()), "tipo1": conteo[1],
            "tipo2": conteo[2], "tipo3": conteo[3]}


def obtener_tendencia(horas: int) -> list[dict[str, int | str]]:
    return [{"hora": (_ahora - timedelta(hours=i)).isoformat(), "total": 0}
            for i in range(horas - 1, -1, -1)]


def obtener_top(limit: int) -> list[dict[str, int | str]]:
    conteo = Counter(alarma.olt for alarma in _alarmas)
    return [{"equipo": equipo, "total": total} for equipo, total in conteo.most_common(limit)]


def obtener_detalle(alarma_id: str) -> Alarma | None:
    return next((alarma for alarma in _alarmas if alarma.id == alarma_id), None)


def reconocer_alarma(alarma_id: str, usuario: str) -> Alarma | None:
    alarma = obtener_detalle(alarma_id)
    if alarma:
        alarma.reconocida_por = usuario
    return alarma
