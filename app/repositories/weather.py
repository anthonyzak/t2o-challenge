"""
Repository for weather data operations.
"""

from datetime import date, datetime
from typing import Dict, List, Optional

import pandas as pd
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.weather import City, WeatherData, WeatherImportLog

logger = get_logger(__name__)


class WeatherRepository:
    """Repository for weather data operations."""

    def __init__(self, db: Session):
        """Initialize repository."""
        self.db = db

    async def get_city_by_name(self, name: str, country: str = None) -> Optional[City]:
        """Get city by name and optional country."""
        query = self.db.query(City).filter(City.name == name)
        if country:
            query = query.filter(City.country == country)
        return query.first()

    async def get_city_by_id(self, id: str) -> Optional[City]:
        """Get city by id."""
        query = self.db.query(City).filter(City.id == id)
        return query.first()

    async def create_city(
        self,
        name: str,
        latitude: float,
        longitude: float,
        country: str = "Spain",
        timezone: str = None,
    ) -> City:
        """Create a new city."""
        city = City(
            name=name,
            latitude=latitude,
            longitude=longitude,
            country=country,
            timezone=timezone,
        )
        self.db.add(city)
        self.db.commit()
        self.db.refresh(city)
        return city

    async def get_weather_data(
        self, city_id: int, start_date: date, end_date: date
    ) -> int:
        """Count weather data records for a city in date range."""
        return (
            self.db.query(WeatherData)
            .filter(
                and_(
                    WeatherData.city_id == city_id,
                    WeatherData.timestamp
                    >= datetime.combine(start_date, datetime.min.time()),
                    WeatherData.timestamp
                    <= datetime.combine(end_date, datetime.max.time()),
                )
            )
            .all()
        )

    async def get_all_weather_data_by_city(
        self,
        city_id: str,
    ) -> List[WeatherData]:
        """Get all weather data filter by city."""
        return self.db.query(WeatherData).filter(WeatherData.city_id == city_id).all()

    async def get_weather_data_date_range(
        self, city_id: str
    ) -> tuple[datetime, datetime] | None:
        """Get min and max dates ranges recorded in weather data"""
        return (
            self.db.query(
                func.min(WeatherData.timestamp), func.max(WeatherData.timestamp)
            )
            .filter(WeatherData.city_id == city_id)
            .first()
        )

    async def delete_weather_data(
        self, city_id: int, start_date: date, end_date: date
    ) -> int:
        """Delete weather data for a city in date range."""
        deleted = (
            self.db.query(WeatherData)
            .filter(
                and_(
                    WeatherData.city_id == city_id,
                    WeatherData.timestamp
                    >= datetime.combine(start_date, datetime.min.time()),
                    WeatherData.timestamp
                    <= datetime.combine(end_date, datetime.max.time()),
                )
            )
            .delete()
        )
        self.db.commit()
        return deleted

    async def bulk_insert_weather_data(
        self, city_id: int, weather_df: pd.DataFrame
    ) -> int:
        """Bulk insert weather data from DataFrame."""
        try:
            records = []
            for _, row in weather_df.iterrows():
                records.append(
                    {
                        "city_id": city_id,
                        "timestamp": row["timestamp"],
                        "temperature": row["temperature"]
                        if pd.notna(row["temperature"])
                        else None,
                        "precipitation": row["precipitation"]
                        if pd.notna(row["precipitation"])
                        else 0.0,
                        "data_source": "open-meteo",
                    }
                )

            if records:
                self.db.bulk_insert_mappings(WeatherData, records)
                self.db.commit()

            return len(records)

        except Exception as e:
            self.db.rollback()
            logger.error(f"Bulk insert failed: {str(e)}")
            raise

    async def log_import(
        self,
        city_id: int,
        start_date: date,
        end_date: date,
        records_imported: int,
        success: bool,
        error_message: str = None,
        duration_seconds: float = None,
    ) -> WeatherImportLog:
        """Log an import operation."""
        log = WeatherImportLog(
            city_id=city_id,
            start_date=datetime.combine(start_date, datetime.min.time()),
            end_date=datetime.combine(end_date, datetime.max.time()),
            records_imported=records_imported,
            success=success,
            error_message=error_message,
            import_duration_seconds=duration_seconds,
        )
        self.db.add(log)
        self.db.commit()
        return log

    async def get_weather_summary(
        self, city_id: int, start_date: date, end_date: date
    ) -> Dict:
        """Get weather summary statistics."""
        result = (
            self.db.query(
                func.avg(WeatherData.temperature).label("temperature_avg"),
                func.min(WeatherData.temperature).label("temperature_min"),
                func.max(WeatherData.temperature).label("temperature_max"),
                func.sum(WeatherData.precipitation).label("precipitation_total"),
                func.count(WeatherData.id).label("record_count"),
            )
            .filter(
                and_(
                    WeatherData.city_id == city_id,
                    WeatherData.timestamp
                    >= datetime.combine(start_date, datetime.min.time()),
                    WeatherData.timestamp
                    <= datetime.combine(end_date, datetime.max.time()),
                )
            )
            .first()
        )

        return {
            "temperature_avg": float(result.temperature_avg or 0),
            "temperature_min": float(result.temperature_min or 0),
            "temperature_max": float(result.temperature_max or 0),
            "precipitation_total": float(result.precipitation_total or 0),
            "record_count": result.record_count or 0,
        }

    async def get_all_cities_with_data(self) -> List[City]:
        """Get all cities that have weather data."""
        return self.db.query(City).join(WeatherData).distinct().all()
