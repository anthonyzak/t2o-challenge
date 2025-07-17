"""
Base model classes with common functionality.
"""

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class BaseModel(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Base model with UUID primary key, timestamps and soft delete functionality."""

    __abstract__ = True

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }
