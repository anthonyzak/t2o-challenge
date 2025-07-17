from sqlalchemy import Boolean, Column, DateTime, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class TimestampMixin:
    """Mixin to add created_at, updated_at and deleted_at timestamps."""

    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=True
    )


class SoftDeleteMixin:
    """Mixin to add soft delete functionality."""

    is_deleted = Column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    deleted_at = Column(DateTime, nullable=True)


class UUIDMixin:
    """Mixin to add UUID primary key."""

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
