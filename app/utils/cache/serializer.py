import json
from typing import Any

from app.core.exceptions import CacheException
from app.core.logging import get_logger

logger = get_logger(__name__)


class CacheSerializer:
    """Simple JSON-only serializer for basic data types."""

    @staticmethod
    def serialize(value: Any) -> bytes:
        """Serialize value to JSON bytes."""
        try:
            return json.dumps(value, default=str, ensure_ascii=False).encode("utf-8")
        except (TypeError, ValueError) as e:
            raise CacheException(f"Serialization failed: {str(e)}")

    @staticmethod
    def deserialize(data: bytes) -> Any:
        """Deserialize JSON bytes to value."""
        try:
            return json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise CacheException(f"Deserialization failed: {str(e)}")
