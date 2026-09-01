from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.middleware.security import add_security_middleware


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        # Connections to the database, queue, and object storage are added here
        # in later milestones so startup failures are explicit and observable.
        yield

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        docs_url=f"{settings.api_v1_prefix}/docs" if settings.enable_docs else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    add_security_middleware(app, settings)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
