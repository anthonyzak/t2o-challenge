from typing import Any, Optional

import redis.asyncio as aioredis
from redis.asyncio import ConnectionPool

from app.core.config import settings
from app.core.exceptions import CacheException
from app.core.logging import get_logger
from app.utils.cache.serializer import CacheSerializer

logger = get_logger(__name__)


class RedisCache:
    """Redis cache for mobile coverage application."""

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis: Optional[aioredis.Redis] = None
        self._pool: Optional[ConnectionPool] = None
        self.serializer = CacheSerializer()

    async def initialize(self) -> None:
        """Initialize Redis connection."""
        try:
            self._pool = ConnectionPool.from_url(
                self.redis_url,
                max_connections=10,
                retry_on_timeout=True,
                socket_connect_timeout=5,
                decode_responses=False,
            )

            self._redis = aioredis.Redis(connection_pool=self._pool)
            await self._redis.ping()

            logger.info("Redis cache initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Redis: {str(e)}")
            raise CacheException(f"Redis initialization failed: {str(e)}")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis."""
        try:
            if not self._redis:
                await self.initialize()

            data = await self._redis.get(key)
            if data is None:
                return None

            return self.serializer.deserialize(data)

        except Exception as e:
            logger.warning(f"Cache get failed for '{key}': {str(e)}")
            return None

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in Redis with optional TTL."""
        try:
            if not self._redis:
                await self.initialize()

            serialized_value = self.serializer.serialize(value)

            if ttl:
                result = await self._redis.setex(key, ttl, serialized_value)
            else:
                result = await self._redis.set(key, serialized_value)

            return bool(result)

        except Exception as e:
            logger.warning(f"Cache set failed for '{key}': {str(e)}")
            return False
