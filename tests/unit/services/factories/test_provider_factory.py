"""
Tests for weather provider factory.
"""

import pytest

from app.services.factories.provider_factory import ProviderType, WeatherProviderFactory
from app.services.providers.openmeteo.geocoding import OpenMeteoGeocodingProvider
from app.services.providers.openmeteo.weather import OpenMeteoWeatherProvider


class TestProviderType:
    """Test ProviderType enum."""

    def test_provider_type_values(self):
        """Test provider type enum values."""
        assert ProviderType.OPENMETEO == "openmeteo"

    def test_provider_type_from_string(self):
        """Test creating provider type from string."""
        provider_type = ProviderType("openmeteo")
        assert provider_type == ProviderType.OPENMETEO

    def test_provider_type_invalid_value(self):
        """Test creating provider type with invalid value."""
        with pytest.raises(ValueError):
            ProviderType("invalid_provider")


class TestWeatherProviderFactory:
    @pytest.mark.parametrize(
        "input_type,expected_class,expected_name",
        [
            (ProviderType.OPENMETEO, OpenMeteoWeatherProvider, "open-meteo"),
            ("openmeteo", OpenMeteoWeatherProvider, "open-meteo"),
        ],
    )
    def test_create_weather_provider(self, input_type, expected_class, expected_name):
        """Test weather provider is created from enum or string input type."""
        provider = WeatherProviderFactory.create_weather_provider(input_type)
        assert isinstance(provider, expected_class)
        assert provider.provider_name == expected_name

    @pytest.mark.parametrize(
        "input_type,expected_class,expected_name",
        [
            (
                ProviderType.OPENMETEO,
                OpenMeteoGeocodingProvider,
                "open-meteo-geocoding",
            ),
            ("openmeteo", OpenMeteoGeocodingProvider, "open-meteo-geocoding"),
        ],
    )
    def test_create_geocoding_provider(self, input_type, expected_class, expected_name):
        """Test geocoding provider is created from enum or string input type."""
        provider = WeatherProviderFactory.create_geocoding_provider(input_type)
        assert isinstance(provider, expected_class)
        assert provider.provider_name == expected_name

    def test_create_weather_provider_unsupported(self):
        """Test error is raised for unsupported weather provider type."""
        with pytest.raises(
            ValueError, match="Weather provider unsupported not supported"
        ):
            WeatherProviderFactory.create_weather_provider("unsupported")

    def test_create_geocoding_provider_unsupported(self):
        """Test error is raised for unsupported geocoding provider type."""
        with pytest.raises(
            ValueError, match="Geocoding provider unsupported not supported"
        ):
            WeatherProviderFactory.create_geocoding_provider("unsupported")

    def test_providers_are_stateless(self):
        """Test providers return new instances on each call (stateless)."""
        p1 = WeatherProviderFactory.create_weather_provider()
        p2 = WeatherProviderFactory.create_weather_provider()
        assert p1 is not p2
        assert type(p1) is type(p2)

        g1 = WeatherProviderFactory.create_geocoding_provider()
        g2 = WeatherProviderFactory.create_geocoding_provider()
        assert g1 is not g2
        assert type(g1) is type(g2)

    def test_provider_interfaces(self):
        """Test providers expose expected methods and attributes."""
        weather = WeatherProviderFactory.create_weather_provider()
        geo = WeatherProviderFactory.create_geocoding_provider()

        assert callable(getattr(weather, "get_historical_weather", None))
        assert isinstance(weather.provider_name, str)

        assert callable(getattr(geo, "search_city", None))
        assert isinstance(geo.provider_name, str)

    def test_error_messages_are_informative(self):
        """Test that provider errors include useful context information."""
        original_weather = WeatherProviderFactory._weather_providers.copy()
        original_geo = WeatherProviderFactory._geocoding_providers.copy()

        WeatherProviderFactory._weather_providers = {}
        WeatherProviderFactory._geocoding_providers = {}

        with pytest.raises(ValueError) as e:
            WeatherProviderFactory.create_weather_provider(ProviderType.OPENMETEO)
        assert "openmeteo" in str(e.value).lower()

        with pytest.raises(ValueError) as e:
            WeatherProviderFactory.create_geocoding_provider(ProviderType.OPENMETEO)
        assert "geocoding" in str(e.value).lower()

        WeatherProviderFactory._weather_providers = original_weather
        WeatherProviderFactory._geocoding_providers = original_geo
