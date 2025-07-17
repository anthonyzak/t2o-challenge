"""
Open-Meteo Weather Archive service.
"""

from datetime import date
from typing import List

import pandas as pd

from app.core.config import settings
from app.core.logging import get_logger
from app.services.providers.base import WeatherDataProvider
from app.services.providers.openmeteo.client import OpenMeteoClient

logger = get_logger(__name__)


class OpenMeteoWeatherProvider(WeatherDataProvider, OpenMeteoClient):
    """Service for Open-Meteo Weather Archive API."""

    def __init__(self):
        """Initialize weather service."""
        super().__init__()
        self.base_url = f"{settings.OPENMETEO_ARCHIVE_URL}/archive"

    @property
    def provider_name(self) -> str:
        return "open-meteo"

    async def get_historical_weather(
        self,
        latitude: float,
        longitude: float,
        start_date: date,
        end_date: date,
        hourly_variables: List[str] = None,
    ) -> pd.DataFrame:
        """
        Get historical weather data for a location.

        Args:
            latitude: Latitude of the location
            longitude: Longitude of the location
            start_date: Start date for data
            end_date: End date for data
            hourly_variables: List of variables to fetch
                (default: temperature, precipitation)

        Returns:
            DataFrame with hourly weather data
        """
        if hourly_variables is None:
            hourly_variables = ["temperature_2m", "precipitation"]

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "hourly": ",".join(hourly_variables),
            "timezone": "Europe/Madrid",
        }

        try:
            logger.info(
                f"Fetching weather data for coordinates ({latitude}, {longitude}) "
                f"from {start_date} to {end_date}"
            )

            data = await self._make_request(self.base_url, params)

            hourly_data = data.get("hourly", {})

            if not hourly_data:
                logger.warning("No hourly data returned from API")
                return pd.DataFrame()

            df = pd.DataFrame(
                {
                    "timestamp": pd.to_datetime(hourly_data["time"]),
                    "temperature": hourly_data.get("temperature_2m", []),
                    "precipitation": hourly_data.get("precipitation", []),
                }
            )

            df["precipitation"] = df["precipitation"].fillna(0.0)

            logger.info(f"Retrieved {len(df)} hourly records")
            return df

        except Exception as e:
            logger.error(f"Failed to fetch weather data: {str(e)}")
            raise
