"""
Main FastAPI application with comprehensive middleware stack.

Implements enterprise-level FastAPI application with proper middleware,
error handling, monitoring, and lifecycle management.
"""

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.exceptions import setup_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.db.session import db_manager
from app.utils.cache.manager import get_cache_manager

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events for proper resource management.
    """
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    try:
        logger.info("Initializing database connection...")
        db_manager.initialize()

        logger.info("Initializing cache manager...")
        await get_cache_manager()

        logger.info("Application startup completed successfully")

        yield

    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise

    logger.info("Shutting down application...")

    try:
        db_manager.close()
        logger.info("Application shutdown completed")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")


def create_application() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI application instance
    """

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="""
        REST API for weather data management and analysis with
        temperature and precipitation statistics.
        """,
        openapi_url=f"{settings.API_V1_STR}/openapi.json"
        if not settings.is_production
        else None,
        docs_url=f"{settings.API_V1_STR}/docs" if not settings.is_production else None,
        redoc_url=f"{settings.API_V1_STR}/redoc"
        if not settings.is_production
        else None,
        lifespan=lifespan,
        generate_unique_id_function=lambda route: f"{route.tags[0]}_{route.name}"
        if route.tags
        else route.name,
    )

    _configure_middleware(app)
    setup_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_V1_STR)
    if not settings.is_production:
        _configure_openapi(app)

    return app


def _configure_middleware(app: FastAPI) -> None:
    """Configure application middleware stack."""

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        """Add request processing time to response headers."""
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(round(process_time, 4))
        return response

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        """Add unique request ID for tracing."""
        import uuid

        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def _configure_openapi(app: FastAPI) -> None:
    """Configure custom OpenAPI schema and documentation."""

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=settings.APP_NAME,
            version=settings.APP_VERSION,
            description=app.description,
            routes=app.routes,
            servers=[
                {
                    "url": f"http://localhost:{settings.PORT}",
                    "description": "Development server",
                },
                {"url": "https://production.com", "description": "Production server"},
            ],
        )

        openapi_schema["info"]["x-logo"] = {
            "url": "https://logo.png",
            "altText": "Weather Data API",
        }

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi

    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Documentation",
            swagger_js_url="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui-bundle.js",  # noqa: E501
            swagger_css_url="https://unpkg.com/swagger-ui-dist@4.15.5/swagger-ui.css",
        )

    @app.get("/redoc", include_in_schema=False)
    async def custom_redoc_html():
        return get_redoc_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Documentation",
            redoc_js_url="https://unpkg.com/redoc@2.0.0/bundles/redoc.standalone.js",
        )


app = create_application()


@app.get("/", tags=["Root"], summary="API Information")
async def root():
    """Get API information and available endpoints."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT.value,
        "status": "running",
        "documentation": {
            "swagger_ui": f"{settings.API_V1_STR}/docs",
            "redoc": f"{settings.API_V1_STR}/redoc",
            "openapi_schema": f"{settings.API_V1_STR}/openapi.json",
        },
    }


# Global exception handler for unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions globally."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "request_id": request.headers.get("X-Request-ID"),
            "timestamp": time.time(),
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        workers=settings.WORKERS if not settings.RELOAD else 1,
        log_config=None,
        access_log=False,
        server_header=False,
        date_header=False,
    )
