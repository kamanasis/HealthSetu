"""HealthSetu Backend Application Entrypoint."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.database import close_database_engine, get_engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.core.middleware import (
    RequestIdMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)

logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle management."""
    settings = get_settings()

    # 1. Startup phase
    setup_logging(log_level=settings.LOG_LEVEL, is_production=settings.is_production)
    logger.info(
        f"Starting {settings.APP_NAME} [env={settings.APP_ENV}, version={settings.APP_VERSION}]"
    )

    # Validate production security constraints
    if settings.is_production:
        if "*" in settings.CORS_ALLOWED_ORIGINS:
            raise RuntimeError("CRITICAL: Wildcard CORS origin '*' is strictly prohibited in production!")

    # Establish database engine boundary (resilient to unavailable DB)
    get_engine()

    yield

    # 2. Shutdown phase
    logger.info(f"Shutting down {settings.APP_NAME}...")
    await close_database_engine()
    logger.info("Shutdown lifecycle complete.")


def create_app(settings: Settings | None = None) -> FastAPI:
    """FastAPI application factory."""
    if settings is None:
        settings = get_settings()

    application = FastAPI(
        title=f"{settings.APP_NAME} API",
        description=(
            "HealthSetu is a unified healthcare interoperability, clinical coordination, "
            "and patient safety backend platform."
        ),
        version=settings.APP_VERSION,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        openapi_url=settings.openapi_url,
        lifespan=lifespan,
    )

    # Configure Middlewares (Order of execution: outer to inner)
    # 1. Security Headers
    application.add_middleware(SecurityHeadersMiddleware)

    # 2. Request payload size limiting
    application.add_middleware(RequestSizeLimitMiddleware)

    # 3. CORS configuration
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=[settings.REQUEST_ID_HEADER],
    )

    # 4. Request ID / Correlation middleware (outermost to track end-to-end timing & ID)
    application.add_middleware(RequestIdMiddleware)

    # Centralized exception handlers
    register_exception_handlers(application)

    # Register API Versioning Routers
    # Mounts /api/v1/... (and future /api/v2/...)
    application.include_router(api_router, prefix="/api")

    return application


app = create_app()
