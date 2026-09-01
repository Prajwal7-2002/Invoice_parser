from fastapi import APIRouter

from app.api.routes import health, uploads

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
