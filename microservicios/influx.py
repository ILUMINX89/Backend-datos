"""Cliente InfluxDB para Trafico Temperatura OLTs."""

from typing import Any

from influxdb_client import InfluxDBClient
from influxdb_client.client.exceptions import InfluxDBError

try:
    from .config import settings
except ImportError:
    from config import settings


def crear_cliente_temp() -> InfluxDBClient:
    return InfluxDBClient(
        url=settings.influx_temp_url,
        token=settings.influx_temp_token,
        org=settings.influx_temp_org,
        timeout=settings.influx_temp_timeout_ms,
        verify_ssl=settings.influx_temp_verify_ssl,
    )


def probar_conexion_temp() -> bool:
    with crear_cliente_temp() as client:
        return bool(client.ping())


def consultar_flux_temp(consulta: str) -> list[dict[str, Any]]:
    try:
        with crear_cliente_temp() as client:
            tablas = client.query_api().query(
                query=consulta,
                org=settings.influx_temp_org,
            )

        registros: list[dict[str, Any]] = []

        for tabla in tablas:
            for registro in tabla.records:
                valores = dict(registro.values)

                valores.pop("result", None)
                valores.pop("table", None)

                registros.append(valores)

        return registros

    except InfluxDBError as exc:
        raise RuntimeError(f"La consulta a InfluxDB TEMP falló: {exc}") from exc
