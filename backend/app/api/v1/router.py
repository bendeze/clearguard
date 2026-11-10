"""ClearGuard API v1 Router Aggregator."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    accountability,
    admin,
    auth,
    blocklists,
    health,
    sync,
    vault,
)

api_v1_router = APIRouter()

# Register endpoint routers
api_v1_router.include_router(health.router)
api_v1_router.include_router(blocklists.router)
api_v1_router.include_router(sync.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(vault.router)
api_v1_router.include_router(accountability.router)
api_v1_router.include_router(admin.router)
