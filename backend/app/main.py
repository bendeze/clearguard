"""ClearGuard FastAPI Application Entry Point."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.database import close_db_engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.migrations import run_startup_migrations
from app.core.security import RateLimitMiddleware, SecurityHeadersMiddleware

logger = logging.getLogger("clearguard.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown events."""
    setup_logging()
    settings = get_settings()
    logger.info(
        "Starting %s v%s [env=%s]",
        settings.app_name,
        settings.app_version,
        settings.app_env,
    )
    await run_startup_migrations(settings=settings)
    yield
    logger.info("Shutting down %s", settings.app_name)
    await close_db_engine()


def create_application() -> FastAPI:
    """Initialize and configure the FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="Backend API and Filtering Intelligence for the ClearGuard Android application",
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Register global exception handlers
    register_exception_handlers(app)

    # Security & CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # Mount versioned API routes
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

    # Root route
    @app.get("/", tags=["System"])
    def read_root() -> dict[str, str]:
        """Root status probe endpoint."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "online",
            "docs": "/docs",
            "health": f"{settings.api_v1_prefix}/health",
        }

    return app


app = create_application()
