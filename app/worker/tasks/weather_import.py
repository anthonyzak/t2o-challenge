"""
Celery tasks for weather data import.
"""

import asyncio
from datetime import date, datetime, timedelta

from celery import current_task

from app.core.logging import get_logger
from app.db.session import db_manager
from app.repositories.weather import WeatherRepository
from app.services.factories.provider_factory import ProviderType, WeatherProviderFactory
from app.worker import celery_app

logger = get_logger(__name__)


@celery_app.task(bind=True, name="weather.import_city_data")
def import_city_weather_data(
    self, city_id: str, start_date: str, end_date: str, provider: str = "openmeteo"
):
    """Import weather data for a specific city using WeatherRepository."""

    async def _async_import():
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
            provider_type = ProviderType(provider)

            db_manager.initialize()

            with db_manager.get_session_context() as db:
                weather_repo = WeatherRepository(db)

                city = await weather_repo.get_city_by_id(id=city_id)

                current_task.update_state(
                    state="PROGRESS",
                    meta={"city": city.name, "status": "fetching_data"},
                )
                existing_data = await weather_repo.get_weather_data(
                    city.id, start_dt, end_dt
                )
                existing_count = len(existing_data)

                if existing_count > 0:
                    logger.info(
                        f"Replacing {existing_count} existing records for {city.name}"
                    )
                    await weather_repo.delete_weather_data(city.id, start_dt, end_dt)

                weather_provider = WeatherProviderFactory.create_weather_provider(
                    provider_type
                )

                current_task.update_state(
                    state="PROGRESS",
                    meta={
                        "city": city.name,
                        "status": "importing",
                        "provider": weather_provider.provider_name,
                    },
                )

                weather_df = await weather_provider.get_historical_weather(
                    latitude=city.latitude,
                    longitude=city.longitude,
                    start_date=start_dt,
                    end_date=end_dt,
                )

                if weather_df.empty:
                    raise ValueError("No weather data returned from provider")

                records_imported = await weather_repo.bulk_insert_weather_data(
                    city_id=city.id, weather_df=weather_df
                )

                duration = (
                    datetime.now() - datetime.strptime(start_date, "%Y-%m-%d")
                ).total_seconds()
                await weather_repo.log_import(
                    city_id=city.id,
                    start_date=start_dt,
                    end_date=end_dt,
                    records_imported=records_imported,
                    success=True,
                    duration_seconds=duration,
                )

                logger.info(
                    f"Successfully imported {records_imported} records for {city.name}"
                )

                return {
                    "city_id": str(city.id),
                    "city_name": city.name,
                    "records_imported": records_imported,
                    "provider_used": weather_provider.provider_name,
                    "date_range": f"{start_date} to {end_date}",
                }

        except Exception as e:
            logger.error(f"Import failed for city {city_id}: {str(e)}")

            if "city" in locals() and city_id:
                with db_manager.get_session_context() as db:
                    weather_repo = WeatherRepository(db)
                    await weather_repo.log_import(
                        city_id=city_id,
                        start_date=start_dt if "start_dt" in locals() else date.today(),
                        end_date=end_dt if "end_dt" in locals() else date.today(),
                        records_imported=0,
                        success=False,
                        error_message=str(e),
                    )

            raise

    return asyncio.run(_async_import())


@celery_app.task(name="weather.import_daily_all_cities")
def import_daily_weather_all_cities():
    """Import yesterday's weather data for all cities using repository."""

    async def _async_import_all():
        try:
            db_manager.initialize()

            with db_manager.get_session_context() as db:
                weather_repo = WeatherRepository(db)
                cities = await weather_repo.get_all_cities_with_data()

                if not cities:
                    logger.info("No cities found for daily import")
                    return {"message": "No cities to process"}

                yesterday = (datetime.now() - timedelta(days=1)).date()

                job_ids = []
                for city in cities:
                    job = import_city_weather_data.delay(
                        city_id=city.id,
                        start_date=yesterday.strftime("%Y-%m-%d"),
                        end_date=yesterday.strftime("%Y-%m-%d"),
                    )
                    job_ids.append(job.id)
                    logger.info(f"Queued daily import for {city.name} (job: {job.id})")

                return {
                    "date": yesterday.strftime("%Y-%m-%d"),
                    "cities_queued": len(cities),
                    "job_ids": job_ids,
                }

        except Exception as e:
            logger.error(f"Daily import scheduling failed: {str(e)}")
            raise

    return asyncio.run(_async_import_all())


@celery_app.task(name="weather.import_missing_city_data")
def import_missing_city_data(city_name: str, country: str = "Spain"):
    """Import data for a city that doesn't exist in DB yet."""

    async def _async_import_new_city():
        try:
            db_manager.initialize()

            with db_manager.get_session_context() as db:
                weather_repo = WeatherRepository(db)

                city = await weather_repo.get_city_by_name(city_name, country)

                if not city:
                    geocoding_provider = (
                        WeatherProviderFactory.create_geocoding_provider()
                    )

                    city_data = await geocoding_provider.search_city(city_name, country)

                    if not city_data:
                        raise ValueError(
                            f"City '{city_name}' not found in geocoding service"
                        )

                    city = await weather_repo.create_city(
                        name=city_data["name"],
                        latitude=city_data["latitude"],
                        longitude=city_data["longitude"],
                        country=city_data.get("country", country),
                        timezone=city_data.get("timezone"),
                    )

                    logger.info(f"Created new city: {city.name}")

                end_date = (datetime.now() - timedelta(days=1)).date()
                start_date = end_date - timedelta(days=7)

                job = import_city_weather_data.delay(
                    city_id=city.id,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                )

                return {
                    "city_id": str(city.id),
                    "city_name": city.name,
                    "import_job_id": job.id,
                    "date_range": f"{start_date} to {end_date}",
                }

        except Exception as e:
            logger.error(f"Failed to import new city {city_name}: {str(e)}")
            raise

    return asyncio.run(_async_import_new_city())
