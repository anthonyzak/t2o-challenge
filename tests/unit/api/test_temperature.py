"""
Tests for temperature endpoints.
"""
from unittest.mock import AsyncMock, Mock, patch

from fastapi import status


class TestTemperatureEndpoints:
    """Test temperature statistics endpoints."""

    @patch("app.api.v1.endpoints.temperature.WeatherStatsService")
    def test_get_temperature_stats_success(self, mock_service_class, client, mock_db):
        """Test successful temperature stats retrieval."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_temperature_stats = AsyncMock(
            return_value={
                "temperature": {
                    "average": 25.5,
                    "max": {"value": 30.0, "date_time": "2024-07-01T15:00"},
                    "min": {"value": 20.0, "date_time": "2024-07-01T06:00"},
                    "hours_above_threshold": 5,
                    "hours_below_threshold": 0,
                }
            }
        )

        response = client.get(
            "/api/v1/temperature/stats",
            params={
                "city": "Madrid",
                "start_date": "2024-07-01",
                "end_date": "2024-07-03",
                "threshold_high": 28.0,
                "threshold_low": 5.0,
            },
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "temperature" in data
        assert data["temperature"]["average"] == 25.5

    def test_get_temperature_stats_invalid_dates(self, client):
        """Test temperature stats with invalid date range."""
        response = client.get(
            "/api/v1/temperature/stats",
            params={
                "city": "Madrid",
                "start_date": "2024-07-03",
                "end_date": "2024-07-01",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert (
            "Start date must be before or equal to end date" in data["error"]["message"]
        )

    @patch("app.api.v1.endpoints.temperature.WeatherStatsService")
    def test_get_temperature_stats_city_not_found(self, mock_service_class, client):
        """Test temperature stats for non-existent city."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_temperature_stats.side_effect = ValueError(
            "City 'NonExistent' not found"
        )

        response = client.get(
            "/api/v1/temperature/stats",
            params={
                "city": "NonExistent",
                "start_date": "2024-07-01",
                "end_date": "2024-07-03",
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "City 'NonExistent' not found" in data["error"]["message"]

    @patch("app.api.v1.endpoints.temperature.WeatherStatsService")
    def test_get_temperature_stats_service_error(self, mock_service_class, client):
        """Test temperature stats with service error."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_temperature_stats.side_effect = Exception("Database error")

        response = client.get(
            "/api/v1/temperature/stats",
            params={
                "city": "Madrid",
                "start_date": "2024-07-01",
                "end_date": "2024-07-03",
            },
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Error calculating statistics" in data["error"]["message"]

    def test_get_temperature_stats_missing_params(self, client):
        """Test temperature stats with missing required parameters."""
        response = client.get("/api/v1/temperature/stats")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
