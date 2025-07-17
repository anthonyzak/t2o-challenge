"""
Open-Meteo Geocoding service.
"""

from typing import Dict, Optional

from app.core.config import settings
from app.core.exceptions import ValidationException
from app.core.logging import get_logger
from app.services.providers.base import GeocodingProvider
from app.services.providers.openmeteo.client import OpenMeteoClient

logger = get_logger(__name__)


class OpenMeteoGeocodingProvider(GeocodingProvider, OpenMeteoClient):
    """Service for Open-Meteo Geocoding API."""

    def __init__(self):
        """Initialize geocoding service."""
        super().__init__()
        self.base_url = f"{settings.OPENMETEO_GEOCODING_URL}/search"

    @property
    def provider_name(self) -> str:
        return "open-meteo-geocoding"

    async def search_city(
        self, city_name: str, country: str = "Spain"
    ) -> Optional[Dict]:
        """
        Search for a city and get its coordinates.

        Args:
            city_name: Name of the city
            country: Country name (default: Spain)

        Returns:
            City information with coordinates or None if not found
        """
        if not city_name or len(city_name.strip()) < 2:
            raise ValidationException("City name must be at least 2 characters")

        params = {
            "name": city_name.strip(),
            "count": 10,
            "language": "en",
            "format": "json",
        }

        try:
            logger.info(f"Searching for city: {city_name}")
            data = await self._make_request(self.base_url, params)

            if not data.get("results"):
                logger.warning(f"No results found for city: {city_name}")
                return None

            results = data["results"]
            if country:
                results = [
                    r
                    for r in results
                    if r.get("country", "").lower() == country.lower()
                ]

            if not results:
                results = data["results"]

            city_data = results[0]

            return {
                "name": city_data.get("name"),
                "latitude": city_data.get("latitude"),
                "longitude": city_data.get("longitude"),
                "country": city_data.get("country", country),
                "timezone": city_data.get("timezone"),
                "population": city_data.get("population"),
                "elevation": city_data.get("elevation"),
            }

        except Exception as e:
            logger.error(f"Geocoding failed for city {city_name}: {str(e)}")
            raise
