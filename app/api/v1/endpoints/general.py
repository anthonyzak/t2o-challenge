"""
General statistics endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.weather import GeneralStatsResponse
from app.services.weather_stats import WeatherStatsService

router = APIRouter()


@router.get(
    "/all",
    response_model=GeneralStatsResponse,
    summary="Get general statistics for all cities",
    description="""
    Get general statistics for all cities with weather data.

    Returns for each city:
    - Date range of available data
    - Average temperature
    - Total precipitation
    - Number of days with precipitation
    - Maximum precipitation day
    - Maximum and minimum temperature days
    """,
)
async def get_general_stats(db: Session = Depends(get_db)):
    """Get general statistics for all cities."""

    try:
        service = WeatherStatsService(db)
        stats = await service.get_general_stats()

        if not stats:
            raise HTTPException(
                status_code=404, detail="No weather data found in the database"
            )

        return stats
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error calculating statistics: {str(e)}"
        )
