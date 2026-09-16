"""Configuracion comun de los microservicios."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # ==========================================
    # Influx - Monitor de red
    # ==========================================

    influx_red_url: str = ""
    influx_red_verify_ssl: bool = False
    influx_red_org: str = ""
    influx_red_token: str = ""
    influx_red_bucket: str = ""
    influx_red_timeout_ms: int = 10000

    # ==========================================
    # Influx - Trafico Temperatura OLTs
    # ==========================================

    influx_temp_url: str = ""
    influx_temp_verify_ssl: bool = False
    influx_temp_org: str = ""
    influx_temp_token: str = ""
    influx_temp_bucket: str = ""
    influx_temp_timeout_ms: int = 10000

    # ==========================================
    # MySQL
    # ==========================================

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = ""
    mysql_password: str = ""
    mysql_database: str = ""
    mysql_connect_timeout: int = 10

    # ==========================================
    # Microservicio alarmas
    # ==========================================

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
