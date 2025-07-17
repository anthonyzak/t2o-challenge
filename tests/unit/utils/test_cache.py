"""
Tests for cache system.
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.exceptions import CacheException
from app.utils.cache.backends.redis import RedisCache
from app.utils.cache.manager import CacheKeyBuilder, CacheManager
from app.utils.cache.serializer import CacheSerializer


class TestCacheKeyBuilder:
    """Test cache key builder."""

    def test_weather_stats_basic(self):
        """Test basic weather stats key generation."""
        key = CacheKeyBuilder.weather_stats(
            city_name="Madrid",
            start_date="2024-07-01",
            end_date="2024-07-03",
            stat_type="temperature",
        )

        expected = "weather:stats:temperature:Madrid:2024-07-01:2024-07-03"
        assert key == expected

    def test_weather_stats_with_thresholds(self):
        """Test weather stats key with thresholds."""
        key = CacheKeyBuilder.weather_stats(
            city_name="Madrid",
            start_date="2024-07-01",
            end_date="2024-07-03",
            stat_type="temperature",
            threshold_high=30.0,
            threshold_low=0.0,
        )

        expected = (
            "weather:stats:temperature:Madrid:2024-07-01:2024-07-03:high=30.0:low=0.0"
        )
        assert key == expected


class TestCacheSerializer:
    """Test cache serializer."""

    def setup_method(self):
        """Set up test method."""
        self.serializer = CacheSerializer()

    def test_serialize_dict(self):
        """Test serializing dictionary."""
        data = {"key": "value", "number": 42}
        result = self.serializer.serialize(data)

        assert isinstance(result, bytes)
        decoded = json.loads(result.decode("utf-8"))
        assert decoded == data

    def test_serialize_list(self):
        """Test serializing list."""
        data = [1, 2, 3, "test"]
        result = self.serializer.serialize(data)

        assert isinstance(result, bytes)
        decoded = json.loads(result.decode("utf-8"))
        assert decoded == data

    def test_serialize_string(self):
        """Test serializing string."""
        data = "test string"
        result = self.serializer.serialize(data)

        assert isinstance(result, bytes)
        decoded = json.loads(result.decode("utf-8"))
        assert decoded == data

    def test_serialize_number(self):
        """Test serializing number."""
        data = 42.5
        result = self.serializer.serialize(data)

        assert isinstance(result, bytes)
        decoded = json.loads(result.decode("utf-8"))
        assert decoded == data

    def test_deserialize_dict(self):
        """Test deserializing dictionary."""
        data = {"key": "value", "number": 42}
        serialized = json.dumps(data).encode("utf-8")
        result = self.serializer.deserialize(serialized)

        assert result == data

    def test_deserialize_invalid_json(self):
        """Test deserializing invalid JSON."""
        invalid_json = b"invalid json"

        with pytest.raises(CacheException, match="Deserialization failed"):
            self.serializer.deserialize(invalid_json)

    def test_deserialize_invalid_encoding(self):
        """Test deserializing with invalid encoding."""
        invalid_bytes = b"\xff\xfe"

        with pytest.raises(CacheException, match="Deserialization failed"):
            self.serializer.deserialize(invalid_bytes)

    def test_serialize_raises_exception_on_invalid_type(self):
        """Test serialize raises CacheException on unserializable object"""
        value = object()
        with patch(
            "app.utils.cache.serializer.json.dumps",
            side_effect=TypeError("Mocked failure"),
        ):
            with pytest.raises(
                CacheException, match="Serialization failed: Mocked failure"
            ):
                self.serializer.serialize(value)


@pytest.mark.asyncio
class TestRedisCache:
    """Test Redis cache backend."""

    def setup_method(self):
        """Set up test method."""
        self.cache = RedisCache("redis://localhost:6379/0")

    @patch("app.utils.cache.backends.redis.aioredis.Redis")
    @patch("app.utils.cache.backends.redis.ConnectionPool")
    async def test_initialize_success(self, mock_pool_class, mock_redis_class):
        """Test successful Redis initialization."""
        mock_pool = Mock()
        mock_pool_class.from_url.return_value = mock_pool

        mock_redis = AsyncMock()
        mock_redis.ping.return_value = "PONG"
        mock_redis_class.return_value = mock_redis

        await self.cache.initialize()

        mock_pool_class.from_url.assert_called_once()
        mock_redis_class.assert_called_once_with(connection_pool=mock_pool)

    @patch("app.utils.cache.backends.redis.aioredis.Redis")
    @patch("app.utils.cache.backends.redis.ConnectionPool")
    async def test_initialize_connection_error(self, mock_pool_class, mock_redis_class):
        """Test Redis initialization with connection error."""
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = Exception("Connection failed")
        mock_redis_class.return_value = mock_redis

        with pytest.raises(CacheException, match="Redis initialization failed"):
            await self.cache.initialize()

    async def test_get_not_initialized(self):
        """Test get operation when not initialized."""
        with patch.object(self.cache, "initialize") as mock_init:
            with patch.object(self.cache, "_redis", None):
                await self.cache.get("test_key")
                mock_init.assert_called_once()

    async def test_get_cache_error(self):
        """Test get operation with cache error."""
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis error")
        self.cache._redis = mock_redis

        result = await self.cache.get("test_key")

        assert result is None

    async def test_set_cache_error(self):
        """Test set operation with cache error."""
        mock_redis = AsyncMock()
        mock_redis.set.side_effect = Exception("Redis error")
        self.cache._redis = mock_redis

        result = await self.cache.set("test_key", "test_value")

        assert result is False

    async def test_get_returns_none_if_key_does_not_exist(self):
        """Test get returns None when key is not found in Redis."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        self.cache._redis = mock_redis

        result = await self.cache.get("nonexistent_key")

        assert result is None
        mock_redis.get.assert_called_once_with("nonexistent_key")

    async def test_get_deserializes_valid_data(self):
        """Test get deserializes returned Redis data."""
        mock_data = b'{"foo": "bar"}'
        mock_redis = AsyncMock()
        mock_redis.get.return_value = mock_data
        self.cache._redis = mock_redis

        with patch.object(
            self.cache.serializer, "deserialize", return_value={"foo": "bar"}
        ) as mock_deserialize:
            result = await self.cache.get("test_key")

            assert result == {"foo": "bar"}
            mock_deserialize.assert_called_once_with(mock_data)

    async def test_set_serializes_and_sets_value_with_ttl(self):
        """Test set serializes data and uses setex when TTL is given."""
        mock_redis = AsyncMock()
        mock_redis.setex.return_value = True
        self.cache._redis = mock_redis

        with patch.object(
            self.cache.serializer, "serialize", return_value=b"serialized"
        ) as mock_serialize:
            result = await self.cache.set("test_key", {"foo": "bar"}, ttl=100)

            assert result is True
            mock_serialize.assert_called_once_with({"foo": "bar"})
            mock_redis.setex.assert_called_once_with("test_key", 100, b"serialized")

    async def test_set_serializes_and_sets_value_without_ttl(self):
        """Test set serializes data and uses set when TTL is not given."""
        mock_redis = AsyncMock()
        mock_redis.set.return_value = True
        self.cache._redis = mock_redis

        with patch.object(
            self.cache.serializer, "serialize", return_value=b"serialized"
        ) as mock_serialize:
            result = await self.cache.set("test_key", {"foo": "bar"})

            assert result is True
            mock_serialize.assert_called_once_with({"foo": "bar"})
            mock_redis.set.assert_called_once_with("test_key", b"serialized")


@pytest.mark.asyncio
class TestCacheManager:
    """Test cache manager."""

    def setup_method(self):
        """Set up test method."""
        self.manager = CacheManager()

    async def test_get_auto_initialize(self):
        """Test get operation with auto-initialization."""
        with patch.object(self.manager, "initialize") as mock_init:
            with patch.object(
                self.manager.redis, "get", return_value="test_value"
            ) as mock_get:
                await self.manager.get("test_key")

                mock_init.assert_called_once()
                mock_get.assert_called_once_with("test_key")

    async def test_set_with_default_ttl(self):
        """Test set operation with default TTL."""
        with patch.object(self.manager, "initialize"):
            with patch.object(self.manager.redis, "set", return_value=True) as mock_set:
                with patch("app.utils.cache.manager.settings") as mock_settings:
                    mock_settings.CACHE_TTL = 3600

                    await self.manager.set("test_key", "test_value")

                    mock_set.assert_called_once_with("test_key", "test_value", 3600)

    async def test_set_with_custom_ttl(self):
        """Test set operation with custom TTL."""
        with patch.object(self.manager, "initialize"):
            with patch.object(self.manager.redis, "set", return_value=True) as mock_set:
                await self.manager.set("test_key", "test_value", ttl=1800)

                mock_set.assert_called_once_with("test_key", "test_value", 1800)

    async def test_initialize_raises_exception_on_failure(self):
        """Test initialize method raises exception on Redis failure."""
        with patch.object(
            self.manager.redis, "initialize", side_effect=Exception("Redis error")
        ):
            with pytest.raises(
                CacheException, match="Cache initialization failed: Redis error"
            ):
                await self.manager.initialize()

    async def test_get_returns_none_on_failure(self):
        """Test get returns None if Redis get fails."""
        with patch.object(self.manager, "initialize"):
            with patch.object(
                self.manager.redis, "get", side_effect=Exception("Get failed")
            ):
                result = await self.manager.get("test_key")
                assert result is None

    async def test_set_returns_false_on_failure(self):
        """Test set returns False if Redis set fails."""
        with patch.object(self.manager, "initialize"):
            with patch.object(
                self.manager.redis, "set", side_effect=Exception("Set failed")
            ):
                result = await self.manager.set("test_key", "test_value", ttl=1200)
                assert result is False
