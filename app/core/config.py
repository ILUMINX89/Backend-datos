from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Backend Datos API"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    influx_url: str = "http://localhost:8086"
    influx_token: str = ""
    influx_org: str = ""
    influx_bucket: str = ""
    influx_timeout_ms: int = 10000

    cors_origins: str = "*"
    allow_raw_flux: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        value = self.cors_origins.strip()
        if value == "*":
            return ["*"]
        return [origin.strip() for origin in value.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
