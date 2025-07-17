"""
Service for calculating weather statistics.
"""

from datetime import date
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.repositories.weather import WeatherRepository
from app.schemas.weather import (
    GeneralStatsResponse,
    PrecipitationStatsResponse,
    TemperatureStatsResponse,
)
from app.utils.cache.manager import CacheKeyBuilder, get_cache_manager

logger = get_logger(__name__)


class WeatherStatsService:
    """Service for weather statistics calculations."""

    def __init__(self, db: Session):
        """Initialize service."""
        self.db = db
        self.weather_repo = WeatherRepository(db)

    async def get_temperature_stats(
        self,
        city_name: str,
        start_date: date,
        end_date: date,
        threshold_high: Optional[float] = None,
        threshold_low: Optional[float] = None,
    ) -> TemperatureStatsResponse:
        """Get temperature statistics for a city."""

        city = await self.weather_repo.get_city_by_name(city_name)
        if not city:
            raise ValueError(f"City '{city_name}' not found")

        cache_key = CacheKeyBuilder.weather_stats(
            city_name,
            str(start_date),
            str(end_date),
            "temperature",
            threshold_high=threshold_high,
            threshold_low=threshold_low,
        )

        cache_manager = await get_cache_manager()
        cached_result = await cache_manager.get(cache_key)

        if cached_result:
            logger.info(f"Temperature stats cache hit for {city_name}")
            return TemperatureStatsResponse(**cached_result)

        logger.info(f"Calculating temperature stats for {city_name}")

        if threshold_high is None:
            threshold_high = settings.DEFAULT_TEMPERATURE_THRESHOLD_HIGH
        if threshold_low is None:
            threshold_low = settings.DEFAULT_TEMPERATURE_THRESHOLD_LOW

        weather_data = await self.weather_repo.get_weather_data(
            city.id,
            start_date,
            end_date,
        )

        if not weather_data:
            raise ValueError(
                f"No weather data found for {city_name} in the specified period"
            )

        df = pd.DataFrame(
            [
                {
                    "timestamp": w.timestamp,
                    "temperature": w.temperature,
                    "date": w.timestamp.date(),
                }
                for w in weather_data
            ]
        )

        stats = {
            "average": round(df["temperature"].mean(), 2),
            "average_by_day": {},
            "max": {},
            "min": {},
            "hours_above_threshold": 0,
            "hours_below_threshold": 0,
        }

        daily_avg = df.groupby("date")["temperature"].mean().round(2)
        stats["average_by_day"] = {
            str(date): float(temp) for date, temp in daily_avg.items()
        }

        max_idx = df["temperature"].idxmax()
        max_row = df.loc[max_idx]
        stats["max"] = {
            "value": float(max_row["temperature"]),
            "date_time": max_row["timestamp"].strftime("%Y-%m-%dT%H:%M"),
        }

        min_idx = df["temperature"].idxmin()
        min_row = df.loc[min_idx]
        stats["min"] = {
            "value": float(min_row["temperature"]),
            "date_time": min_row["timestamp"].strftime("%Y-%m-%dT%H:%M"),
        }

        stats["hours_above_threshold"] = int((df["temperature"] > threshold_high).sum())
        stats["hours_below_threshold"] = int((df["temperature"] < threshold_low).sum())

        result = TemperatureStatsResponse(temperature=stats)
        await cache_manager.set(cache_key, result.dict(), ttl=1800)
        return result

    async def get_precipitation_stats(
        self, city_name: str, start_date: date, end_date: date
    ) -> PrecipitationStatsResponse:
        """Get precipitation statistics for a city."""

        city = await self.weather_repo.get_city_by_name(city_name)
        if not city:
            raise ValueError(f"City '{city_name}' not found")

        cache_key = CacheKeyBuilder.weather_stats(
            city_name, str(start_date), str(end_date), "precipitation"
        )

        cache_manager = await get_cache_manager()
        cached_result = await cache_manager.get(cache_key)

        if cached_result:
            logger.info(f"Precipitation stats cache hit for {city_name}")
            return PrecipitationStatsResponse(**cached_result)

        logger.info(f"Calculating precipitation stats for {city_name}")

        weather_data = await self.weather_repo.get_weather_data(
            city.id, start_date, end_date
        )

        if not weather_data:
            raise ValueError(
                f"No weather data found for {city_name} in the specified period"
            )

        df = pd.DataFrame(
            [
                {
                    "timestamp": w.timestamp,
                    "precipitation": w.precipitation or 0.0,
                    "date": w.timestamp.date(),
                }
                for w in weather_data
            ]
        )

        total_precipitation = df["precipitation"].sum()

        daily_total = df.groupby("date")["precipitation"].sum().round(2)

        days_with_precip = (daily_total > 0).sum()

        if daily_total.max() > 0:
            max_date = daily_total.idxmax()
            max_value = daily_total.max()
        else:
            max_date = daily_total.index[0]
            max_value = 0.0

        total_days = len(daily_total)
        average = total_precipitation / total_days if total_days > 0 else 0.0

        stats = {
            "total": round(float(total_precipitation), 2),
            "total_by_day": {
                str(date): float(precip) for date, precip in daily_total.items()
            },
            "days_with_precipitation": int(days_with_precip),
            "max": {"value": round(float(max_value), 2), "date": str(max_date)},
            "average": round(float(average), 2),
        }
        result = PrecipitationStatsResponse(precipitation=stats)
        await cache_manager.set(cache_key, result.dict(), ttl=1800)
        return result

    async def get_general_stats(self) -> GeneralStatsResponse:
        """Get general statistics for all cities with data."""
        logger.info("Calculating general stats")
        cities = await self.weather_repo.get_all_cities_with_data()

        result = {}

        for city in cities:
            date_range = await self.weather_repo.get_weather_data_date_range(city.id)

            if not date_range[0]:
                continue

            start_date = date_range[0].date()
            end_date = date_range[1].date()

            weather_data = await self.weather_repo.get_all_weather_data_by_city(city.id)

            df = pd.DataFrame(
                [
                    {
                        "timestamp": w.timestamp,
                        "temperature": w.temperature,
                        "precipitation": w.precipitation or 0.0,
                        "date": w.timestamp.date(),
                    }
                    for w in weather_data
                ]
            )

            temp_avg = df["temperature"].mean()
            precip_total = df["precipitation"].sum()

            daily_precip = df.groupby("date")["precipitation"].sum()
            days_with_precip = (daily_precip > 0).sum()

            max_precip_date = daily_precip.idxmax()
            max_precip_value = daily_precip.max()

            temp_max_idx = df["temperature"].idxmax()
            temp_max_date = df.loc[temp_max_idx, "date"]
            temp_max_value = df.loc[temp_max_idx, "temperature"]

            temp_min_idx = df["temperature"].idxmin()
            temp_min_date = df.loc[temp_min_idx, "date"]
            temp_min_value = df.loc[temp_min_idx, "temperature"]

            result[city.name] = {
                "start_date": str(start_date),
                "end_date": str(end_date),
                "temperature_average": round(float(temp_avg), 1),
                "precipitation_total": round(float(precip_total), 1),
                "days_with_precipitation": int(days_with_precip),
                "precipitation_max": {
                    "date": str(max_precip_date),
                    "value": round(float(max_precip_value), 1),
                },
                "temperature_max": {
                    "date": str(temp_max_date),
                    "value": round(float(temp_max_value), 1),
                },
                "temperature_min": {
                    "date": str(temp_min_date),
                    "value": round(float(temp_min_value), 1),
                },
            }
        return GeneralStatsResponse(root=result)
