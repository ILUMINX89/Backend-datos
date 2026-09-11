from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.infrastructure.influx import influx_repository

router = APIRouter()
settings = get_settings()


class FluxQueryRequest(BaseModel):
    query: str = Field(min_length=1)


@router.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok", "service": settings.app_name}


@router.get("/health/influx", tags=["health"])
def health_influx() -> dict:
    try:
        connected = influx_repository.ping()
        if not connected:
            raise HTTPException(status_code=503, detail="InfluxDB is not responding")
        return {"status": "ok", "influx": "connected"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/v1/influx/measurement/{measurement}", tags=["influx"])
def read_measurement(
    measurement: str,
    start: str = Query(default="-1h", description="Flux duration or RFC3339 timestamp"),
    stop: str | None = Query(default=None, description="Optional Flux stop value"),
    limit: int = Query(default=1000, ge=1, le=10000),
) -> dict:
    try:
        rows = influx_repository.query_measurement(
            measurement=measurement,
            start=start,
            stop=stop,
            limit=limit,
        )
        return {"measurement": measurement, "count": len(rows), "data": rows}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/v1/influx/query", tags=["influx"])
def raw_flux_query(payload: FluxQueryRequest) -> dict:
    if not settings.allow_raw_flux:
        raise HTTPException(status_code=403, detail="Raw Flux queries are disabled")

    try:
        rows = influx_repository.query_flux(payload.query)
        return {"count": len(rows), "data": rows}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
