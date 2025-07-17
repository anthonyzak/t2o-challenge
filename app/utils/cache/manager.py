from typing import Any, Optional

from app.core.config import settings
from app.core.exceptions import CacheException
from app.core.logging import get_logger
from app.utils.cache.backends.redis import RedisCache

logger = get_logger(__name__)


class CacheKeyBuilder:
    """Builder to generate consistent cache keys."""

    @staticmethod
    def weather_stats(
        city_name: str,
        start_date: str,
        end_date: str,
        stat_type: str,
        threshold_high: Optional[float] = None,
        threshold_low: Optional[float] = None,
    ) -> str:
        key = f"weather:stats:{stat_type}:{city_name}:{start_date}:{end_date}"

        if threshold_high is not None:
            key += f":high={threshold_high}"
        if threshold_low is not None:
            key += f":low={threshold_low}"

        return key


class CacheManager:
    """Cache manager optimized for Redis only."""

    def __init__(self):
        self.redis = RedisCache()
        self._initialized = False

    async def initialize(self) -> None:
        """Initializes the cache manager."""
        try:
            await self.redis.initialize()
            self._initialized = True
            logger.info("Cache manager initialized with Redis")
        except Exception as e:
            logger.error(f"Failed to initialize cache manager: {str(e)}")
            raise CacheException(f"Cache initialization failed: {str(e)}")

    async def get(self, key: str) -> Optional[Any]:
        """Gets value from cache."""
        if not self._initialized:
            await self.initialize()

        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.warning(f"Cache get failed for key '{key}': {str(e)}")
            return None

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Sets value in cache with TTL."""
        if not self._initialized:
            await self.initialize()

        ttl = ttl or settings.CACHE_TTL

        try:
            return await self.redis.set(key, value, ttl)
        except Exception as e:
            logger.warning(f"Cache set failed for key '{key}': {str(e)}")
            return False


_cache_manager: Optional[CacheManager] = None


async def get_cache_manager() -> CacheManager:
    """Gets or creates the global cache manager."""
    global _cache_manager

    if _cache_manager is None:
        _cache_manager = CacheManager()
        await _cache_manager.initialize()

    return _cache_manager
