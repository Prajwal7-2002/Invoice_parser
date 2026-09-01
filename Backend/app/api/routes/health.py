from fastapi import APIRouter, Response, status

from app.core.config import get_settings
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, include_in_schema=False)
def health_check(response: Response) -> HealthResponse:
    """Liveness endpoint for the load balancer and deployment platform."""
    settings = get_settings()
    response.status_code = status.HTTP_200_OK
    return HealthResponse(status="ok", service=settings.app_name, version=settings.app_version)
