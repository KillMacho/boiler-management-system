"""Mock 1C server settings."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    onec_mock_username: str = "app_user"
    onec_mock_password: str = "password123"
    onec_mock_port: int = 8080
    log_level: str = "INFO"


settings = Settings()
