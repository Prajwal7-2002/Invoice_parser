from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import Settings


def add_security_middleware(app: FastAPI, settings: Settings) -> None:
    """Install safe defaults; production origins are provided via environment variables."""
    allowed_origins = [str(origin).rstrip("/") for origin in settings.cors_origins]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
