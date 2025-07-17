"""
Temperature statistics endpoints.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.schemas.weather import TemperatureStatsResponse
from app.services.weather_stats import WeatherStatsService

router = APIRouter()


@router.get(
    "/stats",
    response_model=TemperatureStatsResponse,
    summary="Get temperature statistics",
    description="""
    Get temperature statistics for a city and date range.

    Returns:
    - Average temperature
    - Average temperature by day
    - Maximum and minimum temperatures with timestamps
    - Hours above/below configurable thresholds
    """,
)
async def get_temperature_stats(
    city: str = Query(..., description="City name"),
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    threshold_high: float = Query(
        default=None,
        description="High temperature threshold "
        f"(default: {settings.DEFAULT_TEMPERATURE_THRESHOLD_HIGH}°C)",
    ),
    threshold_low: float = Query(
        default=None,
        description="Low temperature threshold "
        f"(default: {settings.DEFAULT_TEMPERATURE_THRESHOLD_LOW}°C)",
    ),
    db: Session = Depends(get_db),
):
    """Get temperature statistics for a city."""

    if start_date > end_date:
        raise HTTPException(
            status_code=400, detail="Start date must be before or equal to end date"
        )

    try:
        service = WeatherStatsService(db)
        stats = await service.get_temperature_stats(
            city_name=city,
            start_date=start_date,
            end_date=end_date,
            threshold_high=threshold_high,
            threshold_low=threshold_low,
        )
        return stats
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error calculating statistics: {str(e)}"
        )
