"""
CLI commands for weather data management.
"""

import asyncio
from datetime import date, datetime

import click

from app.core.logging import get_logger, setup_logging
from app.db.session import db_manager
from app.repositories.weather import WeatherRepository
from app.services.factories.provider_factory import ProviderType, WeatherProviderFactory
from app.worker.tasks.weather_import import import_missing_city_data

setup_logging()
logger = get_logger(__name__)


@click.group()
def cli():
    """Weather data management CLI."""
    pass


@cli.command()
@click.argument("city_name")
@click.option("--start-date", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--end-date", required=True, help="End date (YYYY-MM-DD)")
@click.option("--country", default="Spain", help="Country name")
@click.option(
    "--provider",
    type=click.Choice([p.value for p in ProviderType]),
    default=ProviderType.OPENMETEO.value,
    help="Weather data provider to use",
)
def load_weather_data(
    city_name: str,
    start_date: str,
    end_date: str,
    country: str,
    provider: str = "openmeteo",
):
    """Load historical weather data for a city"""

    async def _load_data():
        """Async function to load weather data."""
        start_time = datetime.now()

        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()

            if start_dt > end_dt:
                raise click.BadParameter("Start date must be before end date")

            if end_dt >= date.today():
                raise click.BadParameter("End date must be in the past")

            db_manager.initialize()

            provider_type = ProviderType(provider)
            click.echo(f"Using provider: {provider_type.value}")

            with db_manager.get_session_context() as db:
                weather_repo = WeatherRepository(db)

                city = await weather_repo.get_city_by_name(city_name, country)

                if not city:
                    click.echo(f"Searching for city: {city_name}, {country}")
                    geocoding_provider = (
                        WeatherProviderFactory.create_geocoding_provider(provider_type)
                    )

                    city_data_provider = await geocoding_provider.search_city(
                        city_name, country
                    )

                    if not city_data_provider:
                        raise click.ClickException(f"City '{city_name}' not found")

                    city = await weather_repo.create_city(
                        name=city_data_provider["name"],
                        latitude=city_data_provider["latitude"],
                        longitude=city_data_provider["longitude"],
                        country=city_data_provider.get("country", country),
                        timezone=city_data_provider.get("timezone"),
                    )
                    click.echo(
                        f"Created city: {city.name} ({city.latitude}, {city.longitude})"
                    )

                existing_data = await weather_repo.get_weather_data(
                    city.id, start_dt, end_dt
                )
                existing_count = len(existing_data)
                if existing_count > 0:
                    if not click.confirm(
                        f"Found {existing_count} existing records. Replace them?"
                    ):
                        click.echo("Aborted.")
                        return

                    await weather_repo.delete_weather_data(city.id, start_dt, end_dt)

                click.echo(f"Fetching weather data from {start_date} to {end_date}...")
                weather_provider = WeatherProviderFactory.create_weather_provider(
                    provider_type
                )

                click.echo(f"Provider '{weather_provider.provider_name}' is available")

                weather_df = await weather_provider.get_historical_weather(
                    latitude=city.latitude,
                    longitude=city.longitude,
                    start_date=start_dt,
                    end_date=end_dt,
                )

                if weather_df.empty:
                    raise click.ClickException("No weather data returned from API")

                click.echo(f"Loading {len(weather_df)} hourly records...")
                records_imported = await weather_repo.bulk_insert_weather_data(
                    city_id=city.id, weather_df=weather_df
                )

                duration = (datetime.now() - start_time).total_seconds()
                await weather_repo.log_import(
                    city_id=city.id,
                    start_date=start_dt,
                    end_date=end_dt,
                    records_imported=records_imported,
                    success=True,
                    duration_seconds=duration,
                )

                click.echo(
                    f"Successfully loaded {records_imported} records "
                    f"using {weather_provider.provider_name} in {duration:.2f} seconds"
                )

                summary = await weather_repo.get_weather_summary(
                    city.id, start_dt, end_dt
                )
                click.echo("\nSummary:")
                click.echo(f"  Provider used: {weather_provider.provider_name}")
                click.echo(f"  Average temperature: {summary['temperature_avg']:.1f}°C")
                click.echo(f"  Min temperature: {summary['temperature_min']:.1f}°C")
                click.echo(f"  Max temperature: {summary['temperature_max']:.1f}°C")
                click.echo(
                    f"  Total precipitation: {summary['precipitation_total']:.1f}mm"
                )
        except Exception as e:
            logger.error(f"Failed to load weather data: {str(e)}")

            if "city" in locals() and city:
                with db_manager.get_session_context() as db:
                    weather_repo = WeatherRepository(db)
                    await weather_repo.log_import(
                        city_id=city.id,
                        start_date=start_dt if "start_dt" in locals() else date.today(),
                        end_date=end_dt if "end_dt" in locals() else date.today(),
                        records_imported=0,
                        success=False,
                        error_message=str(e),
                        duration_seconds=(datetime.now() - start_time).total_seconds(),
                    )

            raise click.ClickException(str(e))

    asyncio.run(_load_data())


@cli.command()
def list_cities():
    """List all cities in the database."""

    async def _list_cities():
        db_manager.initialize()

        with db_manager.get_session_context() as db:
            weather_repo = WeatherRepository(db)
            cities = await weather_repo.get_all_cities_with_data()

            if not cities:
                click.echo("No cities found in database.")
                return

            click.echo(f"\nFound {len(cities)} cities:\n")
            click.echo(f"{'Name':<30} {'Country':<20} {'Coordinates':<30} {'Records'}")
            click.echo("-" * 90)

            record_count = len(cities)
            for city in cities:
                coords = f"({city.latitude:.4f}, {city.longitude:.4f})"
                click.echo(
                    f"{city.name:<30} {city.country:<20} {coords:<30} {record_count}"
                )

    asyncio.run(_list_cities())


@cli.command()
@click.argument("city_name")
@click.option("--country", default="Spain", help="Country name")
@click.option(
    "--provider",
    type=click.Choice([p.value for p in ProviderType]),
    default=ProviderType.OPENMETEO.value,
    help="Weather data provider to use",
)
def add_new_city(city_name: str, country: str, provider: str):
    """Add a new city and import recent weather data automatically."""

    async def _check_and_queue():
        try:
            db_manager.initialize()

            with db_manager.get_session_context() as db:
                weather_repo = WeatherRepository(db)

                existing_city = await weather_repo.get_city_by_name(city_name, country)

                if existing_city:
                    click.echo(
                        f"City '{city_name}, {country}' already exists in database"
                    )
                    click.echo("Use 'load_weather_data' command to import more data")
                    return

                import_missing_city_data.delay(city_name=city_name, country=country)
        except Exception as e:
            logger.error(f"Failed to queue new city job: {str(e)}")
            raise click.ClickException(str(e))

    asyncio.run(_check_and_queue())


if __name__ == "__main__":
    cli()
