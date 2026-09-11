from __future__ import annotations

from typing import Any

from influxdb_client import InfluxDBClient
from influxdb_client.client.exceptions import InfluxDBError

from app.core.config import get_settings


class InfluxRepository:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _client(self) -> InfluxDBClient:
        return InfluxDBClient(
            url=self.settings.influx_url,
            token=self.settings.influx_token,
            org=self.settings.influx_org,
            timeout=self.settings.influx_timeout_ms,
        )

    def ping(self) -> bool:
        with self._client() as client:
            return bool(client.ping())

    def query_flux(self, flux: str) -> list[dict[str, Any]]:
        try:
            with self._client() as client:
                tables = client.query_api().query(query=flux, org=self.settings.influx_org)

            rows: list[dict[str, Any]] = []
            for table in tables:
                for record in table.records:
                    values = dict(record.values)
                    values.pop("result", None)
                    values.pop("table", None)
                    rows.append(values)
            return rows
        except InfluxDBError as exc:
            raise RuntimeError(f"InfluxDB query failed: {exc}") from exc

    def query_measurement(
        self,
        measurement: str,
        start: str = "-1h",
        stop: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        safe_measurement = measurement.replace('"', '\\"')
        range_expr = f'range(start: {start}'
        if stop:
            range_expr += f', stop: {stop}'
        range_expr += ')'

        flux = f'''from(bucket: "{self.settings.influx_bucket}")
  |> {range_expr}
  |> filter(fn: (r) => r._measurement == "{safe_measurement}")
  |> limit(n: {limit})'''
        return self.query_flux(flux)


influx_repository = InfluxRepository()
