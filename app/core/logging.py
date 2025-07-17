"""
Structured logging configuration using structlog.

Provides JSON logging for production and human-readable logs for development
with request tracing, performance monitoring, and security auditing.
"""
import logging
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional

import structlog
from pythonjsonlogger import jsonlogger

from app.core.config import settings

request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
session_id_var: ContextVar[Optional[str]] = ContextVar("session_id", default=None)


def inject_context(logger, method_name, event_dict):
    event_dict.update(
        {
            "request_id": request_id_var.get(),
            "user_id": user_id_var.get(),
            "session_id": session_id_var.get(),
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT.value,
        }
    )
    return event_dict


def get_formatter():
    if settings.LOG_FORMAT == "json":

        class CustomJsonFormatter(jsonlogger.JsonFormatter):
            def add_fields(self, log_record, record, message_dict):
                super().add_fields(log_record, record, message_dict)
                log_record.setdefault(
                    "timestamp", datetime.now(timezone.utc).isoformat() + "Z"
                )
                log_record.setdefault("level", record.levelname)
                log_record["logger"] = record.name

        return CustomJsonFormatter("%(message)s")
    else:

        class ColorFormatter(logging.Formatter):
            COLORS = {
                "DEBUG": "\033[36m",
                "INFO": "\033[32m",
                "WARNING": "\033[33m",
                "ERROR": "\033[31m",
                "CRITICAL": "\033[35m",
            }
            RESET = "\033[0m"

            def format(self, record):
                color = self.COLORS.get(record.levelname, "")
                record.levelname = f"{color}{record.levelname}{self.RESET}"
                return super().format(record)

        return ColorFormatter(
            "%(asctime)s | %(levelname)-8s | %(name)-20s | "
            "req:%(request_id)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )


def setup_logging():
    logging.getLogger().handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(get_formatter())
    handler.addFilter(RequestContextFilter())
    logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL), handlers=[handler])

    structlog.configure(
        processors=[
            inject_context,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(colors=settings.is_development)
            if settings.LOG_FORMAT != "json"
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    _configure_log_levels()

    get_logger(__name__).info(
        "Logging configured",
        log_level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
    )


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def _configure_log_levels():
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DATABASE_ECHO else logging.WARNING
    )
    logging.getLogger("app").setLevel(getattr(logging, settings.LOG_LEVEL))


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    return structlog.get_logger(name)
