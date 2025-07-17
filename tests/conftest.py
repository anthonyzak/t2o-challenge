"""
Pytest configuration and fixtures.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.weather import City, WeatherData


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.all.return_value = []
    db.add = Mock()
    db.commit = Mock()
    db.refresh = Mock()
    db.rollback = Mock()
    db.close = Mock()
    return db


@pytest.fixture
def mock_city():
    """Mock city object."""
    city = Mock(spec=City)
    city.id = "123e4567-e89b-12d3-a456-426614174000"
    city.name = "Madrid"
    city.country = "Spain"
    city.latitude = 40.4168
    city.longitude = -3.7038
    city.timezone = "Europe/Madrid"
    return city


@pytest.fixture
def mock_weather_data():
    """Mock weather data list."""
    weather1 = Mock(spec=WeatherData)
    weather1.timestamp = datetime(2024, 7, 1, 12, 0)
    weather1.temperature = 25.5
    weather1.precipitation = 0.0

    weather2 = Mock(spec=WeatherData)
    weather2.timestamp = datetime(2024, 7, 1, 13, 0)
    weather2.temperature = 26.0
    weather2.precipitation = 1.5

    return [weather1, weather2]


@pytest.fixture
def sample_weather_df():
    """Sample weather DataFrame."""
    import pandas as pd

    return pd.DataFrame(
        {
            "timestamp": [datetime(2024, 7, 1, 12, 0), datetime(2024, 7, 1, 13, 0)],
            "temperature": [25.5, 26.0],
            "precipitation": [0.0, 1.5],
        }
    )


@pytest.fixture
def mock_cache_manager():
    """Mock cache manager."""
    cache = AsyncMock()
    cache.get.return_value = None
    cache.set.return_value = True
    return cache


@pytest.fixture
def mock_weather_repo():
    """Mock weather repository."""
    repo = AsyncMock()
    repo.get_city_by_name.return_value = None
    repo.get_weather_data.return_value = []
    repo.create_city.return_value = Mock()
    return repo


@pytest.fixture
def mock_weather_provider():
    """Mock weather provider."""
    provider = AsyncMock()
    provider.provider_name = "test-provider"
    provider.get_historical_weather.return_value = Mock()
    return provider


@pytest.fixture
def mock_geocoding_provider():
    """Mock geocoding provider."""
    provider = AsyncMock()
    provider.provider_name = "test-geocoding"
    provider.search_city.return_value = {
        "name": "Madrid",
        "latitude": 40.4168,
        "longitude": -3.7038,
        "country": "Spain",
        "timezone": "Europe/Madrid",
    }
    return provider
