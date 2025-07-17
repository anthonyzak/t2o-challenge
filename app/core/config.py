"""
Core configuration module using Pydantic Settings for type-safe configuration.
Supports multiple environments and validation of environment variables.
"""

import os
from enum import Enum
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from yarl import URL


class Environment(str, Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """
    Application settings with validation and type safety.
    """

    APP_NAME: str = "Weather Data API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    SECRET_KEY: str = Field(..., min_length=32)
    DEBUG: bool = False

    API_V1_STR: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    ALLOWED_HOSTS: list[str] = ["*"]
    ALLOWED_ORIGINS: list[str] = ["*"]

    DATABASE_HOST: str = Field(
        default="postgres", description="PostgreSQL database host"
    )
    DATABASE_PORT: int = Field(default=5432, description="PostgreSQL database port")
    DATABASE_USER: str = Field(
        default="weather_app", description="PostgreSQL database user"
    )
    DATABASE_PASSWORD: str = Field(
        default="password123", description="PostgreSQL database password"
    )
    DATABASE_NAME: str = Field(
        default="weather_app_db", description="PostgreSQL database name"
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_ECHO: bool = False

    @property
    def DATABASE_URL(self) -> str:
        """
        Assemble database URL from settings.
        Returns a PostgreSQL URL.
        """
        url = URL.build(
            scheme="postgresql",
            user=self.DATABASE_USER,
            password=self.DATABASE_PASSWORD,
            host=self.DATABASE_HOST,
            port=self.DATABASE_PORT,
            path=f"/{self.DATABASE_NAME}",
        )
        return url

    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/0", description="Redis URL"
    )
    CACHE_TTL: int = 3600  # 1 hour

    OPENMETEO_GEOCODING_URL: str = "https://geocoding-api.open-meteo.com/v1"
    OPENMETEO_ARCHIVE_URL: str = "https://archive-api.open-meteo.com/v1"
    OPENMETEO_TIMEOUT: int = 30  # seconds

    DEFAULT_TEMPERATURE_THRESHOLD_HIGH: float = 30.0
    DEFAULT_TEMPERATURE_THRESHOLD_LOW: float = 0.0

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def validate_environment(cls, v):
        """Ensure environment is valid."""
        if isinstance(v, str):
            return Environment(v.lower())
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v):
        """Ensure secret key is secure enough."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

    @field_validator("DATABASE_PORT")
    @classmethod
    def validate_database_port(cls, v):
        """Ensure database port is in valid range."""
        if not 1 <= v <= 65535:
            raise ValueError("DATABASE_PORT must be between 1 and 65535")
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.ENVIRONMENT == Environment.PRODUCTION

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.ENVIRONMENT == Environment.DEVELOPMENT

    @property
    def is_testing(self) -> bool:
        """Check if running in testing."""
        return self.ENVIRONMENT == Environment.TESTING

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        validate_assignment = True


class DevelopmentSettings(Settings):
    """Development-specific settings."""

    DEBUG: bool = True
    RELOAD: bool = True
    DATABASE_ECHO: bool = True
    LOG_LEVEL: str = "DEBUG"

    DATABASE_HOST: str = "db"
    DATABASE_USER: str = "wheater_app"
    DATABASE_PASSWORD: str = "password123"
    DATABASE_NAME: str = "wheater_app_development"


class TestingSettings(Settings):
    """Testing-specific settings."""

    ENVIRONMENT: Environment = Environment.TESTING
    REDIS_URL: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    CACHE_TTL: int = 1

    DATABASE_HOST: str = "db-test"
    DATABASE_USER: str = "wheater_app"
    DATABASE_PASSWORD: str = "password123"
    DATABASE_NAME: str = "wheater_app_test"
    DATABASE_PORT: int = 5432


class ProductionSettings(Settings):
    """Production-specific settings."""

    ENVIRONMENT: Environment = Environment.PRODUCTION
    DEBUG: bool = False
    WORKERS: int = 4
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40


@lru_cache()
def get_settings() -> Settings:
    """
    Factory function to get settings based on environment.
    Uses LRU cache to avoid recreating settings objects.
    """
    environment = os.getenv("ENVIRONMENT", "development").lower()

    settings_map = {
        Environment.DEVELOPMENT: DevelopmentSettings,
        Environment.TESTING: TestingSettings,
        Environment.PRODUCTION: ProductionSettings,
    }

    settings_class = settings_map.get(Environment(environment), Settings)
    return settings_class()


settings = get_settings()
