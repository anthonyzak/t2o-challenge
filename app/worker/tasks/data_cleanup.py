"""
Celery tasks for data cleanup and maintenance.
"""

import asyncio
from datetime import datetime, timedelta

from app.core.logging import get_logger
from app.db.session import db_manager
from app.models.weather import WeatherImportLog
from app.worker import celery_app

logger = get_logger(__name__)


@celery_app.task(name="weather.cleanup_old_data")
def cleanup_old_import_logs():
    """Clean up old import logs using repository pattern."""

    async def _async_cleanup():
        try:
            db_manager.initialize()

            with db_manager.get_session_context() as db:
                cutoff_date = datetime.now() - timedelta(days=30)

                deleted_count = (
                    db.query(WeatherImportLog)
                    .filter(WeatherImportLog.created_at < cutoff_date)
                    .delete()
                )

                db.commit()
                logger.info(f"Cleaned up {deleted_count} old import log entries")

                return {
                    "deleted_logs": deleted_count,
                    "cutoff_date": cutoff_date.isoformat(),
                }

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise

    return asyncio.run(_async_cleanup())
