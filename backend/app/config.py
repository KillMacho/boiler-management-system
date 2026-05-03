"""Application settings loaded from .env via pydantic-settings."""
from __future__ import annotations

from functools import lru_cache
from typing import Annotated, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Database ---
    db_host: str = Field(default="localhost\\SQLEXPRESS")
    db_name: str = Field(default="BoilerManagementDB")
    db_user: str = Field(default="app_backend")
    db_password: str
    db_driver: str = Field(default="ODBC Driver 18 for SQL Server")
    db_trust_cert: str = Field(default="yes")

    # --- JWT ---
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # --- App ---
    app_name: str = "BoilerManagementAPI"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # --- CORS ---
    # NoDecode disables JSON-parsing in pydantic-settings, so the validator
    # below can split the comma-separated env value itself.
    cors_allowed_origins: Annotated[List[str], NoDecode] = Field(default_factory=list)

    # --- 1C Integration ---
    onec_base_url: str = "http://localhost:8080"
    onec_username: str = "app_user"
    onec_password: str = "password123"
    onec_timeout: float = 30.0

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def sqlalchemy_async_url(self) -> str:
        """SQLAlchemy URL for the async aioodbc driver.

        ODBC parameters are URL-encoded in the query string. Driver name
        contains spaces and a plus sign, so wrap it in {curly braces}.
        """
        from urllib.parse import quote_plus

        odbc_str = (
            f"DRIVER={{{self.db_driver}}};"
            f"SERVER={self.db_host};"
            f"DATABASE={self.db_name};"
            f"UID={self.db_user};"
            f"PWD={self.db_password};"
            f"TrustServerCertificate={self.db_trust_cert};"
            f"Encrypt=yes;"
        )
        return f"mssql+aioodbc:///?odbc_connect={quote_plus(odbc_str)}"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
