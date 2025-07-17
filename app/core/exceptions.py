"""
Custom exception handling and error management.

Provides structured exception handling with proper HTTP status codes,
error logging, and user-friendly error messages.
"""

import traceback
from datetime import datetime, timezone
from typing import Any, Dict, Union

import httpx
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from redis.exceptions import RedisError
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


class BaseCustomException(Exception):
    """Base class for custom application exceptions."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: str = None,
        details: Dict[str, Any] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)


class ValidationException(BaseCustomException):
    """Validation error exception."""

    def __init__(self, message: str, field: str = None, details: Dict = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="VALIDATION_ERROR",
            details={"field": field, **(details or {})},
        )


class CacheException(BaseCustomException):
    """Cache operation exception."""

    def __init__(self, message: str, operation: str = None, key: str = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="CACHE_ERROR",
            details={"operation": operation, "key": key},
        )


class ExternalServiceException(BaseCustomException):
    """External service exception."""

    def __init__(self, message: str, service: str = None, status_code: int = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service, "upstream_status": status_code},
        )


class ErrorResponseBuilder:
    """Builder for standardized error responses."""

    @staticmethod
    def build_error_response(
        exception: Union[BaseCustomException, Exception],
        request: Request = None,
        include_traceback: bool = False,
    ) -> Dict[str, Any]:
        """
        Build standardized error response.

        Args:
            exception: The exception to handle
            request: Optional request object for context
            include_traceback: Whether to include traceback (development only)

        Returns:
            Error response dictionary
        """
        request_info = {}
        if request:
            request_info = {
                "method": request.method,
                "url": str(request.url.replace(query=None)),
                "path": request.url.path,
                "request_id": request.headers.get("X-Request-ID"),
            }

        if isinstance(exception, BaseCustomException):
            error_response = {
                "error": {
                    "code": exception.error_code,
                    "message": exception.message,
                    "details": exception.details,
                    "status_code": exception.status_code,
                },
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                **request_info,
            }
        elif isinstance(exception, HTTPException):
            error_response = {
                "error": {
                    "code": "HTTP_ERROR",
                    "message": exception.detail,
                    "status_code": exception.status_code,
                },
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                **request_info,
            }
        elif isinstance(exception, (RequestValidationError, ValidationError)):
            error_response = {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": {
                        "validation_errors": [
                            {
                                "field": error["loc"][-1]
                                if error["loc"]
                                else "unknown",
                                "message": error["msg"],
                                "input": error["input"],
                            }
                            for error in exception.errors()
                        ]
                    },
                    "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                },
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                **request_info,
            }
        elif isinstance(exception, SQLAlchemyError):
            error_code = "DATABASE_ERROR"
            message = "Database operation failed"
            status_code_val = status.HTTP_500_INTERNAL_SERVER_ERROR

            if isinstance(exception, IntegrityError):
                error_code = "INTEGRITY_ERROR"
                message = "Data integrity constraint violation"
                status_code_val = status.HTTP_409_CONFLICT
            elif isinstance(exception, OperationalError):
                error_code = "DATABASE_OPERATIONAL_ERROR"
                message = "Database operational error"

            error_response = {
                "error": {
                    "code": error_code,
                    "message": message,
                    "status_code": status_code_val,
                },
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                **request_info,
            }
        elif isinstance(exception, RedisError):
            error_response = {
                "error": {
                    "code": "CACHE_ERROR",
                    "message": "Cache service error",
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                },
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                **request_info,
            }
        elif isinstance(exception, httpx.HTTPError):
            error_response = {
                "error": {
                    "code": "EXTERNAL_SERVICE_ERROR",
                    "message": "External service error",
                    "status_code": status.HTTP_502_BAD_GATEWAY,
                },
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                **request_info,
            }
        else:
            error_response = {
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                },
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                **request_info,
            }

        if include_traceback:
            error_response["error"]["traceback"] = traceback.format_exc()

        return error_response


def setup_exception_handlers(app: FastAPI) -> None:
    """Setup exception handlers for the FastAPI application."""

    from app.core.config import settings

    @app.exception_handler(BaseCustomException)
    async def custom_exception_handler(request: Request, exc: BaseCustomException):
        """Handle custom application exceptions."""

        logger.error(
            "Custom exception occurred",
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            url=str(request.url),
            method=request.method,
        )

        error_response = ErrorResponseBuilder.build_error_response(
            exc, request, include_traceback=settings.is_development
        )

        return JSONResponse(status_code=exc.status_code, content=error_response)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle FastAPI HTTP exceptions."""

        logger.warning(
            "HTTP exception",
            status_code=exc.status_code,
            detail=exc.detail,
            url=str(request.url),
            method=request.method,
        )

        error_response = ErrorResponseBuilder.build_error_response(exc, request)

        return JSONResponse(
            status_code=exc.status_code,
            content=error_response,
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request, exc):
        logger.warning(
            "Validation error",
            errors=exc.errors(),
            url=str(request.url),
            method=request.method,
        )

        error_response = ErrorResponseBuilder.build_error_response(exc, request)

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=error_response
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """Handle request validation errors."""
        logger.warning(
            "Validation error",
            errors=exc.errors(),
            url=str(request.url),
            method=request.method,
        )

        error_response = ErrorResponseBuilder.build_error_response(exc, request)

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=error_response
        )

    @app.exception_handler(StarletteHTTPException)
    async def starlette_exception_handler(
        request: Request, exc: StarletteHTTPException
    ):
        """Handle Starlette HTTP exceptions."""

        logger.warning(
            "Starlette HTTP exception",
            status_code=exc.status_code,
            detail=exc.detail,
            url=str(request.url),
        )

        error_response = {
            "error": {
                "code": "HTTP_ERROR",
                "message": exc.detail,
                "status_code": exc.status_code,
            },
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "method": request.method,
            "url": str(request.url.replace(query=None)),
            "path": request.url.path,
        }

        return JSONResponse(status_code=exc.status_code, content=error_response)

    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(request: Request, exc: SQLAlchemyError):
        """Handle database exceptions."""

        logger.error(
            "Database error",
            error=str(exc),
            error_type=type(exc).__name__,
            url=str(request.url),
            method=request.method,
            exc_info=True,
        )

        error_response = ErrorResponseBuilder.build_error_response(
            exc, request, include_traceback=settings.is_development
        )

        if settings.is_production:
            error_response["error"]["details"] = {}

        return JSONResponse(
            status_code=error_response["error"]["status_code"], content=error_response
        )

    @app.exception_handler(RedisError)
    async def cache_exception_handler(request: Request, exc: RedisError):
        """Handle cache/Redis exceptions."""

        logger.error(
            "Cache error",
            error=str(exc),
            error_type=type(exc).__name__,
            url=str(request.url),
            method=request.method,
        )

        error_response = ErrorResponseBuilder.build_error_response(exc, request)

        return JSONResponse(
            status_code=error_response["error"]["status_code"], content=error_response
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""

        logger.error(
            "Unexpected error",
            error=str(exc),
            error_type=type(exc).__name__,
            url=str(request.url),
            method=request.method,
            exc_info=True,
        )

        error_response = ErrorResponseBuilder.build_error_response(
            exc, request, include_traceback=settings.is_development
        )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=error_response
        )
