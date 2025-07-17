from abc import ABC, abstractmethod
from datetime import date
from typing import Dict, Optional

import pandas as pd


class WeatherDataProvider(ABC):
    """Interface for weather data providers"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of provider"""
        pass

    @abstractmethod
    async def get_historical_weather(
        self, latitude: float, longitude: float, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """Get historical weather in a range date"""
        pass


class GeocodingProvider(ABC):
    """Interface for geocoding providers"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of provider"""
        pass

    @abstractmethod
    async def search_city(
        self, city_name: str, country: str = "Spain"
    ) -> Optional[Dict]:
        """Search city to geocode"""
        pass
