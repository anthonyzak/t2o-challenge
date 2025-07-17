"""
Base client for Open-Meteo API.
"""

from typing import Any, Dict, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class OpenMeteoClient:
    """Base client for Open-Meteo API requests."""

    def __init__(self, timeout: int = None):
        """Initialize the client."""
        self.timeout = timeout or settings.OPENMETEO_TIMEOUT
        self.headers = {"User-Agent": f"{settings.APP_NAME}/{settings.APP_VERSION}"}

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _make_request(
        self, url: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic."""
        async with httpx.AsyncClient(
            timeout=self.timeout, headers=self.headers
        ) as client:
            try:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
                raise
            except httpx.TimeoutException:
                logger.error(f"Request timeout for URL: {url}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error during request: {str(e)}")
                raise
