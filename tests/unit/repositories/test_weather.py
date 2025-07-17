from datetime import date, datetime
from unittest.mock import Mock

import pandas as pd
import pytest

from app.models import City, WeatherData
from app.repositories.weather import WeatherRepository


@pytest.mark.asyncio
class TestWeatherRepository:
    """Test weather repository."""

    def setup_method(self):
        """Set up test method."""
        self.mock_db = Mock()
        self.repo = WeatherRepository(self.mock_db)

    async def test_get_city_by_name_success(self, mock_city):
        """Test successful city retrieval by name."""
        self.mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = (  # noqa: E501
            mock_city
        )

        result = await self.repo.get_city_by_name("Madrid", "Spain")

        assert result == mock_city
        self.mock_db.query.assert_called_with(City)

    async def test_get_city_by_name_not_found(self):
        """Test city retrieval when city not found."""
        self.mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = (  # noqa: E501
            None
        )

        result = await self.repo.get_city_by_name("Unknown", "Spain")

        assert result is None

    async def test_get_city_by_name_without_country(self, mock_city):
        """Test city retrieval without country filter."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_city
        )

        result = await self.repo.get_city_by_name("Madrid")

        assert result == mock_city
        self.mock_db.query.return_value.filter.assert_called_once()

    async def test_get_city_by_id_success(self, mock_city):
        """Test successful city retrieval by ID."""
        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_city
        )

        result = await self.repo.get_city_by_id("123e4567-e89b-12d3-a456-426614174000")

        assert result == mock_city
        self.mock_db.query.assert_called_with(City)

    async def test_create_city_success(self):
        """Test successful city creation."""
        await self.repo.create_city(
            name="Madrid",
            latitude=40.4168,
            longitude=-3.7038,
            country="Spain",
            timezone="Europe/Madrid",
        )

        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()
        self.mock_db.refresh.assert_called_once()

    async def test_get_weather_data_success(self, mock_weather_data):
        """Test successful weather data retrieval."""
        self.mock_db.query.return_value.filter.return_value.all.return_value = (
            mock_weather_data
        )

        result = await self.repo.get_weather_data(
            city_id="123e4567-e89b-12d3-a456-426614174000",
            start_date=date(2024, 7, 1),
            end_date=date(2024, 7, 3),
        )

        assert result == mock_weather_data
        self.mock_db.query.assert_called_with(WeatherData)

    async def test_get_all_weather_data_by_city(self, mock_weather_data):
        """Test successful weather data retrival by city id"""
        self.mock_db.query.return_value.filter.return_value.all.return_value = (
            mock_weather_data
        )

        result = await self.repo.get_all_weather_data_by_city(city_id="1")

        assert result == mock_weather_data
        self.mock_db.query.assert_called_once_with(WeatherData)

    async def test_get_weather_data_date_range(self):
        """Test successful getting weather data min and max ranges"""
        min_date = datetime(2023, 1, 1)
        max_date = datetime(2023, 12, 31)
        mock_result = (min_date, max_date)
        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_result
        )

        result = await self.repo.get_weather_data_date_range(city_id="1")

        assert result == (min_date, max_date)
        self.mock_db.query.assert_called_once()

    async def test_delete_weather_data_success(self):
        """Test successful weather data deletion."""
        self.mock_db.query.return_value.filter.return_value.delete.return_value = 5

        result = await self.repo.delete_weather_data(
            city_id="123e4567-e89b-12d3-a456-426614174000",
            start_date=date(2024, 7, 1),
            end_date=date(2024, 7, 3),
        )

        assert result == 5
        self.mock_db.query.return_value.filter.return_value.delete.assert_called_once()
        self.mock_db.commit.assert_called_once()

    async def test_bulk_insert_weather_data_success(self, sample_weather_df):
        """Test successful bulk insert of weather data."""
        result = await self.repo.bulk_insert_weather_data(
            city_id="123e4567-e89b-12d3-a456-426614174000", weather_df=sample_weather_df
        )

        assert result == len(sample_weather_df)
        self.mock_db.bulk_insert_mappings.assert_called_once()
        self.mock_db.commit.assert_called_once()

    async def test_bulk_insert_weather_data_empty_df(self):
        """Test bulk insert with empty DataFrame."""
        empty_df = pd.DataFrame()

        result = await self.repo.bulk_insert_weather_data(
            city_id="123e4567-e89b-12d3-a456-426614174000", weather_df=empty_df
        )

        assert result == 0
        self.mock_db.bulk_insert_mappings.assert_not_called()

    async def test_bulk_insert_weather_data_error(self, sample_weather_df):
        """Test bulk insert with database error."""
        self.mock_db.bulk_insert_mappings.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            await self.repo.bulk_insert_weather_data(
                city_id="123e4567-e89b-12d3-a456-426614174000",
                weather_df=sample_weather_df,
            )

        self.mock_db.rollback.assert_called_once()

    async def test_log_import_success(self):
        """Test successful import logging."""
        await self.repo.log_import(
            city_id="123e4567-e89b-12d3-a456-426614174000",
            start_date=date(2024, 7, 1),
            end_date=date(2024, 7, 3),
            records_imported=100,
            success=True,
            duration_seconds=45.5,
        )

        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()

    async def test_log_import_with_error(self):
        """Test import logging with error message."""
        await self.repo.log_import(
            city_id="123e4567-e89b-12d3-a456-426614174000",
            start_date=date(2024, 7, 1),
            end_date=date(2024, 7, 3),
            records_imported=0,
            success=False,
            error_message="API timeout",
        )

        self.mock_db.add.assert_called_once()
        self.mock_db.commit.assert_called_once()

    async def test_get_weather_summary_success(self):
        """Test successful weather summary retrieval."""
        mock_result = Mock(
            temperature_avg=25.5,
            temperature_min=20.0,
            temperature_max=30.0,
            precipitation_total=15.8,
            record_count=48,
        )
        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_result
        )

        result = await self.repo.get_weather_summary(
            city_id="123e4567-e89b-12d3-a456-426614174000",
            start_date=date(2024, 7, 1),
            end_date=date(2024, 7, 3),
        )

        assert result == {
            "temperature_avg": 25.5,
            "temperature_min": 20.0,
            "temperature_max": 30.0,
            "precipitation_total": 15.8,
            "record_count": 48,
        }

    async def test_get_weather_summary_no_data(self):
        """Test weather summary with no data."""
        mock_result = Mock(
            temperature_avg=None,
            temperature_min=None,
            temperature_max=None,
            precipitation_total=None,
            record_count=0,
        )
        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_result
        )

        result = await self.repo.get_weather_summary(
            city_id="123e4567-e89b-12d3-a456-426614174000",
            start_date=date(2024, 7, 1),
            end_date=date(2024, 7, 3),
        )

        assert result == {
            "temperature_avg": 0.0,
            "temperature_min": 0.0,
            "temperature_max": 0.0,
            "precipitation_total": 0.0,
            "record_count": 0,
        }

    async def test_get_all_cities_with_data_success(self, mock_city):
        """Test successful retrieval of cities with data."""
        self.mock_db.query.return_value.join.return_value.distinct.return_value.all.return_value = [  # noqa: E501
            mock_city
        ]

        result = await self.repo.get_all_cities_with_data()

        assert result == [mock_city]
        self.mock_db.query.assert_called_with(City)

    async def test_get_all_cities_with_data_empty(self):
        """Test retrieval of cities when no data available."""
        self.mock_db.query.return_value.join.return_value.distinct.return_value.all.return_value = (  # noqa: E501
            []
        )

        result = await self.repo.get_all_cities_with_data()

        assert result == []
