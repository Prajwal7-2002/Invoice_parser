from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr
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

    # Extraction stays off until authentication exists; enable it locally for testing.
    extraction_enabled: bool = False
    max_upload_bytes: int = 10 * 1024 * 1024
    max_pages: int = 5
    # Longest image side sent to the model; caps token cost without hurting legibility.
    max_image_side: int = 2000

    # OCR binaries are on PATH in the Docker image; set these only on hosts where they are not.
    tesseract_cmd: str | None = None
    poppler_path: str | None = None

    openrouter_api_key: SecretStr | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "qwen/qwen2.5-vl-72b-instruct"
    llm_timeout_seconds: float = 90.0
    llm_max_attempts: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
