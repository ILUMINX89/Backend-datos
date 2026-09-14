"""Cliente mínimo para probar la conexión y ejecutar consultas Flux."""

from typing import Any

from influxdb_client import InfluxDBClient
from influxdb_client.client.exceptions import InfluxDBError

try:
    from .config import settings
except ImportError:  # Permite ejecutar los scripts auxiliares directamente.
    from config import settings


def crear_cliente() -> InfluxDBClient:
    return InfluxDBClient(
        url=settings.influx_url,
        token=settings.influx_token,
        org=settings.influx_org,
        timeout=settings.influx_timeout_ms,
        verify_ssl=settings.influx_verify_ssl,
    )


def probar_conexion() -> bool:
    with crear_cliente() as client:
        return bool(client.ping())


def consultar_flux(consulta: str) -> list[dict[str, Any]]:
    try:
        with crear_cliente() as client:
            tablas = client.query_api().query(
                query=consulta,
                org=settings.influx_org,
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
        raise RuntimeError(f"La consulta a InfluxDB falló: {exc}") from exc
