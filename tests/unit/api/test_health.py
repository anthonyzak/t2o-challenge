"""
Tests for health endpoints.
"""

from unittest.mock import AsyncMock, Mock, patch

from fastapi import status


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check_success(self, client):
        """Test basic health check endpoint."""
        response = client.get("/api/v1/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "weather-api"
        assert "timestamp" in data

    @patch("app.api.v1.endpoints.health.get_db")
    @patch("app.api.v1.endpoints.health.get_cache_manager")
    def test_detailed_health_check_success(
        self, mock_cache_manager, mock_get_db, client
    ):
        """Test detailed health check with all services healthy."""
        mock_db = Mock()
        mock_db.execute.return_value.scalar.return_value = 1
        mock_get_db.return_value = mock_db

        mock_cache = AsyncMock()
        mock_cache_manager.return_value = mock_cache

        response = client.get("/api/v1/health/detailed")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert "services" in data
        assert "database" in data["services"]
        assert "cache" in data["services"]

    @patch("app.api.v1.endpoints.health.get_cache_manager")
    def test_detailed_health_check_database_error(self, mock_cache_manager, client):
        """Test detailed health check with database error."""
        from app.api.v1.endpoints.health import get_db
        from app.main import app

        def mock_get_db():
            mock_db = Mock()
            mock_db.execute.side_effect = Exception("Database connection failed")
            return mock_db

        app.dependency_overrides[get_db] = mock_get_db

        mock_cache = AsyncMock()
        mock_cache.get.return_value = None
        mock_cache_manager.return_value = mock_cache

        response = client.get("/api/v1/health/detailed")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "degraded"
        assert data["services"]["database"]["status"] == "unhealthy"
        assert data["services"]["cache"]["status"] == "healthy"

        app.dependency_overrides = {}

    @patch("app.api.v1.endpoints.health.get_db")
    @patch("app.api.v1.endpoints.health.get_cache_manager")
    def test_detailed_health_check_cache_error(
        self, mock_cache_manager, mock_get_db, client
    ):
        """Test detailed health check with cache error."""
        mock_db = Mock()
        mock_db.execute.return_value.scalar.return_value = 1
        mock_get_db.return_value = mock_db

        mock_cache_manager.side_effect = Exception("Cache connection failed")

        response = client.get("/api/v1/health/detailed")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["database"]["status"] == "healthy"
        assert data["services"]["cache"]["status"] == "unhealthy"

    @patch("app.api.v1.endpoints.health.HealthResponse")
    def test_detailed_health_check_general_error(self, health_response_mock, client):
        """Test detailed health check with general error."""
        from app.api.v1.endpoints.health import get_db
        from app.main import app

        def mock_get_db():
            return Mock()

        app.dependency_overrides[get_db] = mock_get_db

        health_response_mock.side_effect = Exception("Critical system error")

        response = client.get("/api/v1/health/detailed")

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "error" in data
        assert "Health check failed" in data["error"]["message"]

        app.dependency_overrides = {}
