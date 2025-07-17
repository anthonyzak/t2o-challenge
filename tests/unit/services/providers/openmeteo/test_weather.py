from datetime import date
from unittest.mock import patch

import pandas as pd
import pytest

from app.services.providers.openmeteo.weather import OpenMeteoWeatherProvider


@pytest.mark.asyncio
class TestOpenMeteoWeatherProvider:
    def setup_method(self):
        """Initialize OpenMeteoWeatherProvider before each test."""
        self.provider = OpenMeteoWeatherProvider()

    def test_provider_name(self):
        """Test that provider_name is set correctly."""
        assert self.provider.provider_name == "open-meteo"

    @pytest.mark.parametrize(
        "mock_response, expected_len, expected_temp, expected_precip",
        [
            (
                {
                    "hourly": {
                        "time": ["2024-07-01T12:00", "2024-07-01T13:00"],
                        "temperature_2m": [25.5, 26.0],
                        "precipitation": [0.0, 1.5],
                    }
                },
                2,
                25.5,
                1.5,
            ),
            ({}, 0, None, None),
            (
                {
                    "hourly": {
                        "time": ["2024-07-01T12:00", "2024-07-01T13:00"],
                        "temperature_2m": [25.5, 26.0],
                        "precipitation": [None, 1.5],
                    }
                },
                2,
                25.5,
                1.5,
            ),
        ],
    )
    @patch(
        "app.services.providers.openmeteo.weather.OpenMeteoWeatherProvider._make_request"
    )
    async def test_get_historical_weather_various_cases(
        self, mock_request, mock_response, expected_len, expected_temp, expected_precip
    ):
        """Test weather data parsing with normal, empty, and null responses."""
        mock_request.return_value = mock_response

        result = await self.provider.get_historical_weather(
            latitude=40.4168,
            longitude=-3.7038,
            start_date=date(2024, 7, 1),
            end_date=date(2024, 7, 3),
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == expected_len

        if expected_len > 0:
            assert "timestamp" in result.columns
            assert "temperature" in result.columns
            assert "precipitation" in result.columns
            if expected_temp is not None:
                assert result["temperature"].iloc[0] == expected_temp
            if expected_precip is not None:
                assert result["precipitation"].iloc[-1] == expected_precip

    @patch(
        "app.services.providers.openmeteo.weather.OpenMeteoWeatherProvider._make_request"
    )
    async def test_get_historical_weather_custom_variables(self, mock_request):
        """Test custom hourly variables are passed correctly in the request."""
        mock_response = {
            "hourly": {
                "time": ["2024-07-01T12:00"],
                "temperature_2m": [25.5],
                "precipitation": [0.0],
                "humidity": [65.0],
            }
        }
        mock_request.return_value = mock_response

        await self.provider.get_historical_weather(
            latitude=40.4168,
            longitude=-3.7038,
            start_date=date(2024, 7, 1),
            end_date=date(2024, 7, 3),
            hourly_variables=["temperature_2m", "precipitation", "humidity"],
        )

        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        assert "temperature_2m,precipitation,humidity" in args[1]["hourly"]

    @patch(
        "app.services.providers.openmeteo.weather.OpenMeteoWeatherProvider._make_request"
    )
    async def test_get_historical_weather_api_error(self, mock_request):
        """Test that exceptions raised in the API call are propagated."""
        mock_request.side_effect = Exception("API request failed")

        with pytest.raises(Exception, match="API request failed"):
            await self.provider.get_historical_weather(
                latitude=40.4168,
                longitude=-3.7038,
                start_date=date(2024, 7, 1),
                end_date=date(2024, 7, 3),
            )

    async def test_get_historical_weather_request_params(self):
        """Test the API request is built with correct parameters."""
        with patch.object(self.provider, "_make_request") as mock_request:
            mock_request.return_value = {
                "hourly": {"time": [], "temperature_2m": [], "precipitation": []}
            }

            await self.provider.get_historical_weather(
                latitude=40.4168,
                longitude=-3.7038,
                start_date=date(2024, 7, 1),
                end_date=date(2024, 7, 3),
            )

            params = mock_request.call_args[0][1]

            assert params == {
                "latitude": 40.4168,
                "longitude": -3.7038,
                "start_date": "2024-07-01",
                "end_date": "2024-07-03",
                "hourly": "temperature_2m,precipitation",
                "timezone": "Europe/Madrid",
            }
