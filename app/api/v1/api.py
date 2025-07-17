"""
API v1 router configuration.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import general, health, precipitation, temperature

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(
    temperature.router, prefix="/temperature", tags=["Temperature"]
)
api_router.include_router(
    precipitation.router, prefix="/precipitation", tags=["Precipitation"]
)
api_router.include_router(
    general.router, prefix="/statistics", tags=["General Statistics"]
)
