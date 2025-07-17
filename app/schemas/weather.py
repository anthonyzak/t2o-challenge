"""
Pydantic schemas for weather data.
"""

from datetime import date
from typing import Any, Dict

from pydantic import BaseModel, Field, RootModel


class TemperatureStatsResponse(BaseModel):
    """Response schema for temperature statistics."""

    temperature: Dict = Field(description="Temperature statistics")

    class Config:
        schema_extra = {
            "example": {
                "temperature": {
                    "average": 18.7,
                    "average_by_day": {
                        "2024-07-01": 18.7,
                        "2024-07-02": 18.8,
                        "2024-07-03": 18.9,
                    },
                    "max": {"value": 33.2, "date_time": "2024-07-01T15:00"},
                    "min": {"value": 7.1, "date_time": "2024-07-01T06:00"},
                    "hours_above_threshold": 5,
                    "hours_below_threshold": 2,
                }
            }
        }


class PrecipitationStatsResponse(BaseModel):
    """Response schema for precipitation statistics."""

    precipitation: Dict = Field(description="Precipitation statistics")

    class Config:
        schema_extra = {
            "example": {
                "precipitation": {
                    "total": 5.8,
                    "total_by_day": {
                        "2024-07-01": 1.5,
                        "2024-07-02": 0.6,
                        "2024-07-03": 3.7,
                    },
                    "days_with_precipitation": 3,
                    "max": {"value": 1.5, "date": "2024-07-01"},
                    "average": 1.93,
                }
            }
        }


class CityWeatherSummary(BaseModel):
    """Weather summary for a city."""

    start_date: date
    end_date: date
    temperature_average: float
    precipitation_total: float
    days_with_precipitation: int
    precipitation_max: Dict[str, Any]
    temperature_max: Dict[str, Any]
    temperature_min: Dict[str, Any]


class GeneralStatsResponse(RootModel[Dict[str, CityWeatherSummary]]):
    """Response schema for general statistics."""

    class Config:
        schema_extra = {
            "example": {
                "Madrid": {
                    "start_date": "2024-07-01",
                    "end_date": "2024-07-03",
                    "temperature_average": 18.7,
                    "precipitation_total": 5.8,
                    "days_with_precipitation": 4,
                    "precipitation_max": {"date": "2024-07-01", "value": 1.5},
                    "temperature_max": {"date": "2024-07-01", "value": 33.2},
                    "temperature_min": {"date": "2024-07-03", "value": 17.1},
                }
            }
        }
