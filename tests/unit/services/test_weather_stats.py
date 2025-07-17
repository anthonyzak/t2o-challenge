"""
Tests for weather statistics service.
"""

from datetime import date, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.schemas.weather import PrecipitationStatsResponse, TemperatureStatsResponse
from app.services.weather_stats import WeatherStatsService


@pytest.mark.asyncio
class TestWeatherStatsService:
    """Test weather statistics service."""

    def setup_method(self):
        """Set up test method."""
        self.mock_db = Mock()
        self.service = WeatherStatsService(self.mock_db)

    @patch("app.services.weather_stats.get_cache_manager")
    async def test_get_temperature_stats_success(
        self, mock_cache_manager, mock_city, mock_weather_data
    ):
        """Test successful temperature stats calculation."""
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        mock_cache.set.return_value = True
        mock_cache_manager.return_value = mock_cache

        self.service.weather_repo = AsyncMock()
        self.service.weather_repo.get_city_by_name.return_value = mock_city
        self.service.weather_repo.get_weather_data.return_value = mock_weather_data

        result = await self.service.get_temperature_stats(
            city_name="Madrid", start_date=date(2024, 7, 1), end_date=date(2024, 7, 3)
        )

        assert result is not None
        assert hasattr(result, "temperature")

    @patch("app.services.weather_stats.get_cache_manager")
    async def test_get_temperature_stats_cached(self, mock_cache_manager, mock_city):
        """Test temperature stats with cached data."""
        cached_data = {
            "temperature": {
                "average": 25.5,
                "max": {"value": 30.0, "date_time": "2024-07-01T15:00"},
                "min": {"value": 20.0, "date_time": "2024-07-01T06:00"},
            }
        }
        mock_cache = AsyncMock()
        mock_cache.get.return_value = cached_data
        mock_cache_manager.return_value = mock_cache

        self.service.weather_repo = AsyncMock()
        self.service.weather_repo.get_city_by_name.return_value = mock_city

        result = await self.service.get_temperature_stats(
            city_name="Madrid", start_date=date(2024, 7, 1), end_date=date(2024, 7, 3)
        )

        assert isinstance(result, TemperatureStatsResponse)
        mock_cache.get.assert_called_once()

    async def test_get_temperature_stats_city_not_found(self):
        """Test temperature stats when city is not found."""
        self.service.weather_repo = AsyncMock()
        self.service.weather_repo.get_city_by_name.return_value = None

        with pytest.raises(ValueError, match="City 'Unknown' not found"):
            await self.service.get_temperature_stats(
                city_name="Unknown",
                start_date=date(2024, 7, 1),
                end_date=date(2024, 7, 3),
            )

    @patch("app.services.weather_stats.get_cache_manager")
    async def test_get_temperature_stats_no_data(self, mock_cache_manager, mock_city):
        """Test temperature stats when no weather data available."""
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        mock_cache_manager.return_value = mock_cache

        self.service.weather_repo = AsyncMock()
        self.service.weather_repo.get_city_by_name.return_value = mock_city
        self.service.weather_repo.get_weather_data.return_value = []

        with pytest.raises(ValueError, match="No weather data found"):
            await self.service.get_temperature_stats(
                city_name="Madrid",
                start_date=date(2024, 7, 1),
                end_date=date(2024, 7, 3),
            )

    @patch("app.services.weather_stats.get_cache_manager")
    async def test_get_precipitation_stats_success(
        self, mock_cache_manager, mock_city, mock_weather_data
    ):
        """Test successful precipitation stats calculation."""
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        mock_cache.set.return_value = True
        mock_cache_manager.return_value = mock_cache

        self.service.weather_repo = AsyncMock()
        self.service.weather_repo.get_city_by_name.return_value = mock_city
        self.service.weather_repo.get_weather_data.return_value = mock_weather_data

        result = await self.service.get_precipitation_stats(
            city_name="Madrid", start_date=date(2024, 7, 1), end_date=date(2024, 7, 3)
        )

        assert result is not None
        assert hasattr(result, "precipitation")

    @patch("app.services.weather_stats.get_cache_manager")
    async def test_get_precipitation_stats_cached(self, mock_cache_manager, mock_city):
        """Test precipitation stats with cached data."""
        cached_data = {
            "precipitation": {
                "total": 15.8,
                "days_with_precipitation": 2,
                "average": 5.27,
            }
        }
        mock_cache = AsyncMock()
        mock_cache.get.return_value = cached_data
        mock_cache_manager.return_value = mock_cache

        self.service.weather_repo = AsyncMock()
        self.service.weather_repo.get_city_by_name.return_value = mock_city

        result = await self.service.get_precipitation_stats(
            city_name="Madrid", start_date=date(2024, 7, 1), end_date=date(2024, 7, 3)
        )

        assert isinstance(result, PrecipitationStatsResponse)
        mock_cache.get.assert_called_once()

    async def test_get_precipitation_stats_city_not_found(self):
        """Test precipitation stats when city is not found."""
        self.service.weather_repo = AsyncMock()
        self.service.weather_repo.get_city_by_name.return_value = None

        with pytest.raises(ValueError, match="City 'Unknown' not found"):
            await self.service.get_precipitation_stats(
                city_name="Unknown",
                start_date=date(2024, 7, 1),
                end_date=date(2024, 7, 3),
            )

    @patch("app.services.weather_stats.get_cache_manager")
    async def test_get_precipitation_stats_no_data(self, mock_cache_manager, mock_city):
        """Test precipitation stats when no weather data available."""
        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        mock_cache_manager.return_value = mock_cache

        self.service.weather_repo = AsyncMock()
        self.service.weather_repo.get_city_by_name.return_value = mock_city
        self.service.weather_repo.get_weather_data.return_value = []

        with pytest.raises(ValueError, match="No weather data found"):
            await self.service.get_precipitation_stats(
                city_name="Madrid",
                start_date=date(2024, 7, 1),
                end_date=date(2024, 7, 3),
            )

    async def test_get_general_stats_success(self, mock_city):
        """Test successful general stats calculation."""
        self.service.weather_repo = AsyncMock()
        self.service.weather_repo.get_all_cities_with_data.return_value = [mock_city]

        date_range_result = (datetime(2024, 7, 1), datetime(2024, 7, 3))
        self.service.weather_repo.get_weather_data_date_range.return_value = (
            date_range_result
        )

        mock_weather = Mock()
        mock_weather.timestamp = datetime(2024, 7, 1, 12, 0)
        mock_weather.temperature = 25.5
        mock_weather.precipitation = 1.5
        self.service.weather_repo.get_all_weather_data_by_city.return_value = [
            mock_weather
        ]

        result = await self.service.get_general_stats()

        assert result is not None
        self.service.weather_repo.get_all_cities_with_data.assert_called_once()

    async def test_get_general_stats_no_cities(self):
        """Test general stats when no cities available."""
        self.service.weather_repo = AsyncMock()
        self.service.weather_repo.get_all_cities_with_data.return_value = []

        result = await self.service.get_general_stats()

        assert result.root == {}
