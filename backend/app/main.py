"""ClearGuard FastAPI Application Entry Point."""

from fastapi import FastAPI

app = FastAPI(
    title="ClearGuard API",
    description="Backend API and Filtering Intelligence for the ClearGuard Android application",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


@app.get("/")
def read_root() -> dict[str, str]:
    """Root health and status endpoint."""
    return {
        "message": "ClearGuard API",
        "version": "0.1.0",
        "status": "online",
    }

