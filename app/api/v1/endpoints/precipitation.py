"""
Precipitation statistics endpoints.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.weather import PrecipitationStatsResponse
from app.services.weather_stats import WeatherStatsService

router = APIRouter()


@router.get(
    "/stats",
    response_model=PrecipitationStatsResponse,
    summary="Get precipitation statistics",
    description="""
    Get precipitation statistics for a city and date range.

    Returns:
    - Total precipitation
    - Total precipitation by day
    - Average precipitation
    - Number of days with precipitation
    - Day with maximum precipitation
    """,
)
async def get_precipitation_stats(
    city: str = Query(..., description="City name"),
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """Get precipitation statistics for a city."""

    if start_date > end_date:
        raise HTTPException(
            status_code=400, detail="Start date must be before or equal to end date"
        )

    try:
        service = WeatherStatsService(db)
        stats = await service.get_precipitation_stats(
            city_name=city, start_date=start_date, end_date=end_date
        )
        return stats
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error calculating statistics: {str(e)}"
        )
