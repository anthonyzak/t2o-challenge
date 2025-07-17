"""
Database models for weather data.
"""
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class City(BaseModel):
    """Model for storing city information."""

    __tablename__ = "cities"

    name = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    country = Column(String(100), default="Spain")
    timezone = Column(String(50), nullable=True)

    weather_data = relationship(
        "WeatherData", back_populates="city", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("name", "country", name="uq_city_name_country"),
        Index("idx_city_coordinates", "latitude", "longitude"),
    )

    def __repr__(self):
        return f"<City(name='{self.name}', country='{self.country}')>"


class WeatherData(BaseModel):
    """Model for storing hourly weather data."""

    __tablename__ = "weather_data"

    city_id = Column(
        UUID(as_uuid=True), ForeignKey("cities.id", ondelete="CASCADE"), nullable=False
    )
    timestamp = Column(DateTime, nullable=False)
    temperature = Column(Float, nullable=True)
    precipitation = Column(Float, nullable=True, default=0.0)

    humidity = Column(Float, nullable=True)
    wind_speed = Column(Float, nullable=True)

    data_source = Column(String(50), default="open-meteo")

    city = relationship("City", back_populates="weather_data")

    __table_args__ = (
        UniqueConstraint("city_id", "timestamp", name="uq_weather_city_timestamp"),
        Index("idx_weather_city_date", "city_id", "timestamp"),
        Index("idx_weather_timestamp", "timestamp"),
    )

    def __repr__(self):
        return f"<WeatherData(city_id={self.city_id}, timestamp='{self.timestamp}')>"


class WeatherImportLog(BaseModel):
    """Model for tracking weather data imports."""

    __tablename__ = "weather_import_logs"

    city_id = Column(
        UUID(as_uuid=True), ForeignKey("cities.id", ondelete="CASCADE"), nullable=False
    )
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    records_imported = Column(Integer, default=0)
    success = Column(Boolean, default=True)
    error_message = Column(String(500), nullable=True)
    import_duration_seconds = Column(Float, nullable=True)

    city = relationship("City")

    def __repr__(self):
        return (
            f"<WeatherImportLog(city_id={self.city_id},"
            f"dates={self.start_date} to {self.end_date})>"
        )
