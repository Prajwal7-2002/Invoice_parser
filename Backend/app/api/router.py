from fastapi import APIRouter

from app.api.routes import extractions, health, uploads

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(uploads.router, prefix="/uploads", tags=["uploads"])
api_router.include_router(extractions.router, prefix="/extractions", tags=["extractions"])
