"""
Tests for precipitation endpoints.
"""

from unittest.mock import AsyncMock, Mock, patch

from fastapi import status


class TestPrecipitationEndpoints:
    """Test precipitation statistics endpoints."""

    @patch("app.api.v1.endpoints.precipitation.WeatherStatsService")
    def test_get_precipitation_stats_success(self, mock_service_class, client):
        """Test successful precipitation stats retrieval."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_precipitation_stats = AsyncMock(
            return_value={
                "precipitation": {
                    "total": 15.8,
                    "total_by_day": {
                        "2024-07-01": 5.2,
                        "2024-07-02": 0.0,
                        "2024-07-03": 10.6,
                    },
                    "days_with_precipitation": 2,
                    "max": {"value": 10.6, "date": "2024-07-03"},
                    "average": 5.27,
                }
            }
        )

        response = client.get(
            "/api/v1/precipitation/stats",
            params={
                "city": "Madrid",
                "start_date": "2024-07-01",
                "end_date": "2024-07-03",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "precipitation" in data
        assert data["precipitation"]["total"] == 15.8
        assert data["precipitation"]["days_with_precipitation"] == 2

    def test_get_precipitation_stats_invalid_dates(self, client):
        """Test precipitation stats with invalid date range."""
        response = client.get(
            "/api/v1/precipitation/stats",
            params={
                "city": "Madrid",
                "start_date": "2024-07-05",
                "end_date": "2024-07-01",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert (
            "Start date must be before or equal to end date" in data["error"]["message"]
        )

    @patch("app.api.v1.endpoints.precipitation.WeatherStatsService")
    def test_get_precipitation_stats_city_not_found(self, mock_service_class, client):
        """Test precipitation stats for non-existent city."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_precipitation_stats.side_effect = ValueError(
            "City 'Unknown' not found"
        )

        response = client.get(
            "/api/v1/precipitation/stats",
            params={
                "city": "Unknown",
                "start_date": "2024-07-01",
                "end_date": "2024-07-03",
            },
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "City 'Unknown' not found" in data["error"]["message"]

    @patch("app.api.v1.endpoints.precipitation.WeatherStatsService")
    def test_get_precipitation_stats_service_error(self, mock_service_class, client):
        """Test precipitation stats with service error."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_precipitation_stats.side_effect = Exception(
            "Database connection lost"
        )

        response = client.get(
            "/api/v1/precipitation/stats",
            params={
                "city": "Madrid",
                "start_date": "2024-07-01",
                "end_date": "2024-07-03",
            },
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Error calculating statistics" in data["error"]["message"]

    def test_get_precipitation_stats_missing_params(self, client):
        """Test precipitation stats with missing required parameters."""
        response = client.get("/api/v1/precipitation/stats", params={"city": "Madrid"})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
