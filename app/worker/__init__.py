"""
Celery worker configuration for weather data processing.
"""

from celery import Celery
from kombu import Queue

from app.core.config import settings


def create_celery_app() -> Celery:
    """Create and configure Celery application."""

    celery_app = Celery(
        "weather_worker",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
        include=[
            "app.worker.tasks.weather_import",
            "app.worker.tasks.data_cleanup",
        ],
    )

    celery_app.conf.update(
        task_routes={
            "weather.import_city_data": {"queue": "weather_import"},
            "weather.import_daily_all_cities": {"queue": "weather_import"},
            "weather.import_missing_city_data": {"queue": "weather_import"},
            "weather.cleanup_old_data": {"queue": "maintenance"},
        },
        task_queues=(
            Queue("weather_import", routing_key="weather_import"),
            Queue("maintenance", routing_key="maintenance"),
        ),
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        beat_schedule={
            "import-daily-weather": {
                "task": "weather.import_daily_all_cities",
                "schedule": 86400,
            },
            "cleanup-old-logs": {
                "task": "weather.cleanup_old_data",
                "schedule": 86400,
            },
        },
    )

    return celery_app


celery_app = create_celery_app()
