"""
Health check response schema.
"""

from datetime import datetime, timezone
from typing import Dict

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(description="Overall health status")
    version: str = Field(description="API version")
    timestamp: datetime = Field(default_factory=datetime.now(timezone.utc))
    services: Dict[str, Dict] = Field(description="Status of individual services")

    class Config:
        schema_extra = {
            "example": {
                "status": "healthy",
                "version": "1.0.0",
                "timestamp": "2024-01-15T10:30:00Z",
                "services": {
                    "database": {
                        "status": "healthy",
                        "response_time_ms": 12,
                        "connection_pool": {"active": 5, "idle": 15, "total": 20},
                    },
                    "cache": {
                        "status": "healthy",
                        "response_time_ms": 3,
                        "memory_usage_mb": 128,
                    },
                    "geocoding_api": {
                        "status": "healthy",
                        "response_time_ms": 45,
                        "rate_limit_remaining": 850,
                    },
                },
            }
        }
