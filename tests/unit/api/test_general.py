"""
Tests for general statistics endpoints.
"""

from unittest.mock import AsyncMock, Mock, patch

from fastapi import status


class TestGeneralEndpoints:
    """Test general statistics endpoints."""

    @patch("app.api.v1.endpoints.general.WeatherStatsService")
    def test_get_general_stats_success(self, mock_service_class, client):
        """Test successful general stats retrieval."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_general_stats = AsyncMock(
            return_value={
                "Madrid": {
                    "start_date": "2024-07-01",
                    "end_date": "2024-07-03",
                    "temperature_average": 25.5,
                    "precipitation_total": 15.8,
                    "days_with_precipitation": 2,
                    "precipitation_max": {"date": "2024-07-03", "value": 10.6},
                    "temperature_max": {"date": "2024-07-02", "value": 30.0},
                    "temperature_min": {"date": "2024-07-01", "value": 20.0},
                },
                "Barcelona": {
                    "start_date": "2024-07-01",
                    "end_date": "2024-07-03",
                    "temperature_average": 23.2,
                    "precipitation_total": 8.5,
                    "days_with_precipitation": 1,
                    "precipitation_max": {"date": "2024-07-02", "value": 8.5},
                    "temperature_max": {"date": "2024-07-03", "value": 28.5},
                    "temperature_min": {"date": "2024-07-01", "value": 18.0},
                },
            }
        )

        response = client.get("/api/v1/statistics/all")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "Madrid" in data
        assert "Barcelona" in data
        assert data["Madrid"]["temperature_average"] == 25.5
        assert data["Barcelona"]["precipitation_total"] == 8.5

    @patch("app.api.v1.endpoints.general.WeatherStatsService")
    def test_get_general_stats_no_data(self, mock_service_class, client):
        """Test general stats when no data is available."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_general_stats = AsyncMock(return_value=None)

        response = client.get("/api/v1/statistics/all")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "No weather data found in the database" in data["error"]["message"]

    @patch("app.api.v1.endpoints.general.WeatherStatsService")
    def test_get_general_stats_service_error(self, mock_service_class, client):
        """Test general stats with service error."""
        mock_service = Mock()
        mock_service_class.return_value = mock_service
        mock_service.get_general_stats.side_effect = Exception(
            "Database connection error"
        )

        response = client.get("/api/v1/statistics/all")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Error calculating statistics" in data["error"]["message"]
