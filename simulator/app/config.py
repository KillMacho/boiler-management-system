"""Simulator configuration via pydantic-settings (reads from .env)."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    backend_url: str = "http://localhost:8000"
    admin_username: str = "admin"
    admin_password: str = "admin123"

    num_boilers: int = 15
    send_interval: float = 30.0       # seconds between readings
    alarm_min_interval: float = 1800  # 30 min minimum between alarms
    alarm_max_interval: float = 5400  # 90 min maximum between alarms
    enable_alarms: bool = True
    log_level: str = "INFO"


settings = Settings()
