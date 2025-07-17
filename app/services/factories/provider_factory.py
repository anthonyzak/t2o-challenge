from enum import Enum
from typing import Dict, Type

from app.core.logging import get_logger
from app.services.providers.base import GeocodingProvider, WeatherDataProvider
from app.services.providers.openmeteo.geocoding import OpenMeteoGeocodingProvider
from app.services.providers.openmeteo.weather import OpenMeteoWeatherProvider

logger = get_logger(__name__)


class ProviderType(str, Enum):
    OPENMETEO = "openmeteo"


class WeatherProviderFactory:
    """Factory to create weather data providers."""

    _weather_providers: Dict[ProviderType, Type[WeatherDataProvider]] = {
        ProviderType.OPENMETEO: OpenMeteoWeatherProvider,
    }

    _geocoding_providers: Dict[ProviderType, Type[GeocodingProvider]] = {
        ProviderType.OPENMETEO: OpenMeteoGeocodingProvider,
    }

    @classmethod
    def create_weather_provider(
        cls, provider_type: ProviderType = ProviderType.OPENMETEO
    ) -> WeatherDataProvider:
        """Creates a weather data provider."""
        if provider_type not in cls._weather_providers:
            raise ValueError(f"Weather provider {provider_type} not supported")

        provider_class = cls._weather_providers[provider_type]
        return provider_class()

    @classmethod
    def create_geocoding_provider(
        cls, provider_type: ProviderType = ProviderType.OPENMETEO
    ) -> GeocodingProvider:
        """Creates a geocoding provider."""
        if provider_type not in cls._geocoding_providers:
            raise ValueError(f"Geocoding provider {provider_type} not supported")

        provider_class = cls._geocoding_providers[provider_type]
        return provider_class()
