"""Configuracion comun de los microservicios, cargada desde el entorno."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    influx_url: str = "http://127.0.0.1:8086"
    influx_token: str = ""
    influx_org: str = ""
    influx_bucket: str = ""
    influx_timeout_ms: int = 10000
    influx_verify_ssl: bool = False

    alarmas_service_host: str = "127.0.0.1"
    alarmas_service_port: int = 8001

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
