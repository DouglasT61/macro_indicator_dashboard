from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Macro Stress Dashboard"
    app_env: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8005
    frontend_origin: str = "http://127.0.0.1:4173"
    database_url: str = "sqlite:///./backend/data/macro_dashboard.db"
    demo_mode: bool = True
    scheduler_enabled: bool = True
    bootstrap_on_startup: bool = True
    refresh_hour: int = 6
    refresh_minute: int = 0
    enable_alerts: bool = True
    regime_config_path: Path = Field(default=BACKEND_ROOT / "config" / "regime_config.json")
    fred_api_key: str | None = None
    eia_api_key: str | None = None
    market_data_api_key: str | None = None
    aishub_username: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def normalized_database_url(self) -> str:
        url = self.database_url.strip()
        if url.startswith("postgres://"):
            return "postgresql+psycopg://" + url.removeprefix("postgres://")
        if url.startswith("postgresql://") and "+psycopg" not in url:
            return "postgresql+psycopg://" + url.removeprefix("postgresql://")
        return url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

