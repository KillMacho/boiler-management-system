"""EDO mock server settings."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    edo_mock_api_key: str = "demo_api_key_replace_in_production"
    edo_mock_port: int = 8081
    log_level: str = "INFO"
    storage_dir: str = "storage/submissions"


settings = Settings()
