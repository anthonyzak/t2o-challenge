"""
Tests for OpenMeteo geocoding provider.
"""

from unittest.mock import patch

import pytest

from app.core.exceptions import ValidationException
from app.services.providers.openmeteo.geocoding import OpenMeteoGeocodingProvider


@pytest.mark.asyncio
class TestOpenMeteoGeocodingProvider:
    """Test OpenMeteo geocoding provider."""

    def setup_method(self):
        """Set up test method."""
        self.provider = OpenMeteoGeocodingProvider()

    def test_provider_name(self):
        """Test provider name property."""
        assert self.provider.provider_name == "open-meteo-geocoding"

    @patch(
        "app.services.providers.openmeteo.geocoding."
        "OpenMeteoGeocodingProvider._make_request"
    )
    @pytest.mark.parametrize(
        "mock_response, expected",
        [
            (
                {
                    "results": [
                        {
                            "name": "Madrid",
                            "latitude": 40.4168,
                            "longitude": -3.7038,
                            "country": "Spain",
                            "timezone": "Europe/Madrid",
                            "population": 3223000,
                            "elevation": 667,
                        }
                    ]
                },
                {
                    "name": "Madrid",
                    "latitude": 40.4168,
                    "longitude": -3.7038,
                    "country": "Spain",
                    "timezone": "Europe/Madrid",
                },
            ),
            ({"results": []}, None),
            ({}, None),
        ],
    )
    async def test_search_city_various_responses(
        self, mock_request, mock_response, expected
    ):
        """Test successful city search, no results, and missing results key."""
        mock_request.return_value = mock_response
        result = await self.provider.search_city("Madrid", "Spain")

        if expected is None:
            assert result is None
        else:
            for key, value in expected.items():
                assert result[key] == value

    @patch(
        "app.services.providers.openmeteo.geocoding."
        "OpenMeteoGeocodingProvider._make_request"
    )
    async def test_search_city_country_filter(self, mock_request):
        """Test city search with country filtering."""
        mock_request.return_value = {
            "results": [
                {
                    "name": "Madrid",
                    "latitude": 40.4168,
                    "longitude": -3.7038,
                    "country": "Spain",
                },
                {
                    "name": "Madrid",
                    "latitude": 40.0,
                    "longitude": -84.0,
                    "country": "United States",
                },
            ]
        }

        result = await self.provider.search_city("Madrid", "Spain")

        assert result["country"] == "Spain"
        assert result["latitude"] == 40.4168

    @patch(
        "app.services.providers.openmeteo.geocoding."
        "OpenMeteoGeocodingProvider._make_request"
    )
    async def test_search_city_fallback_no_country_match(self, mock_request):
        """Test city search fallback when no country match."""
        mock_request.return_value = {
            "results": [
                {
                    "name": "Madrid",
                    "latitude": 40.0,
                    "longitude": -84.0,
                    "country": "United States",
                }
            ]
        }

        result = await self.provider.search_city("Madrid", "France")

        assert result is not None
        assert result["country"] == "United States"

    @pytest.mark.parametrize("invalid_name", ["", "M", "   "])
    async def test_search_city_invalid_name(self, invalid_name):
        """Test city search with empty, too short, or whitespace name."""
        with pytest.raises(
            ValidationException, match="City name must be at least 2 characters"
        ):
            await self.provider.search_city(invalid_name, "Spain")

    @patch(
        "app.services.providers.openmeteo.geocoding."
        "OpenMeteoGeocodingProvider._make_request"
    )
    async def test_search_city_without_country(self, mock_request):
        """Test city search without specifying country."""
        mock_request.return_value = {
            "results": [
                {
                    "name": "Madrid",
                    "latitude": 40.4168,
                    "longitude": -3.7038,
                    "country": "Spain",
                }
            ]
        }

        result = await self.provider.search_city("Madrid")

        assert result is not None
        assert result["name"] == "Madrid"

    @patch(
        "app.services.providers.openmeteo.geocoding."
        "OpenMeteoGeocodingProvider._make_request"
    )
    async def test_search_city_api_error(self, mock_request):
        """Test city search with API error."""
        mock_request.side_effect = Exception("API request failed")

        with pytest.raises(Exception, match="API request failed"):
            await self.provider.search_city("Madrid", "Spain")

    async def test_search_city_request_params(self):
        """Test that request parameters are correctly formatted."""
        with patch.object(self.provider, "_make_request") as mock_request:
            mock_request.return_value = {"results": []}

            await self.provider.search_city("Madrid", "Spain")

            call_args = mock_request.call_args
            params = call_args[0][1]

            assert params["name"] == "Madrid"
            assert params["count"] == 10
            assert params["language"] == "en"
            assert params["format"] == "json"

    @patch(
        "app.services.providers.openmeteo.geocoding."
        "OpenMeteoGeocodingProvider._make_request"
    )
    async def test_search_city_partial_data(self, mock_request):
        """Test city search with partial data in response."""
        mock_request.return_value = {
            "results": [{"name": "Madrid", "latitude": 40.4168, "longitude": -3.7038}]
        }

        result = await self.provider.search_city("Madrid", "Spain")

        assert result is not None
        assert result["name"] == "Madrid"
        assert result["country"] == "Spain"
        assert result["timezone"] is None
        assert result["population"] is None
        assert result["elevation"] is None
