"""
Tests for OpenMeteo client.
"""
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
import tenacity

from app.services.providers.openmeteo.client import OpenMeteoClient


@pytest.mark.asyncio
class TestOpenMeteoClient:
    """Test OpenMeteo client."""

    def setup_method(self):
        """Set up test method."""
        self.client = OpenMeteoClient()

    def test_client_initialization_default(self):
        """Test client initialization with default values."""
        client = OpenMeteoClient()

        assert client.timeout == 30
        assert "User-Agent" in client.headers
        assert "Weather Data API" in client.headers["User-Agent"]

    def test_client_initialization_custom_timeout(self):
        """Test client initialization with custom timeout."""
        client = OpenMeteoClient(timeout=60)

        assert client.timeout == 60

    @patch("app.services.providers.openmeteo.client.httpx.AsyncClient")
    async def test_make_request_success(self, mock_client_class):
        """Test successful HTTP request."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.json.return_value = {"result": "success"}
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        result = await self.client._make_request("http://test.com", {"param": "value"})

        assert result == {"result": "success"}
        mock_client.get.assert_called_once_with(
            "http://test.com", params={"param": "value"}
        )
        mock_response.raise_for_status.assert_called_once()

    @patch("app.services.providers.openmeteo.client.httpx.AsyncClient")
    async def test_make_request_without_params(self, mock_client_class):
        """Test HTTP request without parameters."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.json.return_value = {"data": "test"}
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        result = await self.client._make_request("http://test.com")

        assert result == {"data": "test"}
        mock_client.get.assert_called_once_with("http://test.com", params=None)

    @patch("app.services.providers.openmeteo.client.httpx.AsyncClient")
    async def test_make_request_http_error(self, mock_client_class):
        """Test HTTP request with HTTP error."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=Mock(), response=mock_response
        )
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        with pytest.raises(tenacity.RetryError) as exc_info:
            await self.client._make_request("http://test.com")

        assert isinstance(
            exc_info.value.last_attempt.exception(), httpx.HTTPStatusError
        )

    @patch("app.services.providers.openmeteo.client.httpx.AsyncClient")
    async def test_make_request_timeout_error(self, mock_client_class):
        """Test HTTP request with timeout error."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("Request timeout")
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        with pytest.raises(tenacity.RetryError) as exc_info:
            await self.client._make_request("http://test.com")

        assert isinstance(
            exc_info.value.last_attempt.exception(), httpx.TimeoutException
        )

    @patch("app.services.providers.openmeteo.client.httpx.AsyncClient")
    async def test_make_request_generic_error(self, mock_client_class):
        """Test HTTP request with generic error."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection failed")
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        with pytest.raises(tenacity.RetryError) as exc_info:
            await self.client._make_request("http://test.com")

        assert isinstance(exc_info.value.last_attempt.exception(), Exception)
        assert "Connection failed" in str(exc_info.value.last_attempt.exception())

    @patch("app.services.providers.openmeteo.client.httpx.AsyncClient")
    async def test_make_request_retry_logic(self, mock_client_class):
        """Test retry logic on failures."""
        mock_client = AsyncMock()
        mock_response_success = Mock()
        mock_response_success.json.return_value = {"result": "success"}
        mock_response_success.raise_for_status.return_value = None

        mock_client.get.side_effect = [
            httpx.TimeoutException("Timeout 1"),
            httpx.TimeoutException("Timeout 2"),
            mock_response_success,
        ]
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        result = await self.client._make_request("http://test.com")

        assert result == {"result": "success"}
        assert mock_client.get.call_count == 3

    @patch("app.services.providers.openmeteo.client.httpx.AsyncClient")
    async def test_make_request_json_parsing(self, mock_client_class):
        """Test JSON response parsing."""
        mock_client = AsyncMock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [1, 2, 3],
            "metadata": {"count": 3},
            "status": "ok",
        }
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__.return_value = None

        result = await self.client._make_request("http://test.com")

        assert result["data"] == [1, 2, 3]
        assert result["metadata"]["count"] == 3
        assert result["status"] == "ok"
