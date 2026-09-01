from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Secrets are injected by the hosting platform."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "staging", "production"] = "development"
    app_name: str = "Invoice Parser API"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    enable_docs: bool = True
    log_level: str = "INFO"
    cors_origins: list[AnyHttpUrl] = Field(default_factory=list)

    # These are intentionally optional during foundation work. Production startup
    # validation will require the appropriate values before upload routes are enabled.
    database_url: str | None = None
    redis_url: str | None = None
    r2_endpoint_url: str | None = None
    r2_bucket_name: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
