"""ClearGuard Admin emergency early deactivation override endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.auth import CurrentAdminUser
from app.core.database import DbSession
from app.schemas.admin import (
    AdminClientListResponse,
    AdminDeviceListResponse,
    AdminOverrideCreateRequest,
    AdminOverrideResponse,
    AdminPendingRequestItem,
    AdminPublicKeyResponse,
)
from app.services.admin_service import AdminService, get_admin_service

router = APIRouter(prefix="/admin", tags=["ClearGuard Admin Early Override"])
AdminServiceDep = Annotated[AdminService, Depends(get_admin_service)]


@router.get(
    "/override-requests/pending",
    summary="List active deactivation requests pending admin review",
)
async def list_pending_override_requests(
    _: CurrentAdminUser,
    db: DbSession,
    admin_service: AdminServiceDep,
) -> list[AdminPendingRequestItem]:
    """Retrieve all active deactivation requests available for administrative intervention."""
    return await admin_service.list_pending_requests(db)


@router.post(
    "/override-requests/approve",
    status_code=status.HTTP_201_CREATED,
    summary="Approve emergency early override with Ed25519 asymmetric signature",
)
async def approve_override(
    request: AdminOverrideCreateRequest,
    current_admin: CurrentAdminUser,
    db: DbSession,
    admin_service: AdminServiceDep,
) -> AdminOverrideResponse:
    """Issue a cryptographically signed override certificate for emergency early deactivation."""
    return await admin_service.approve_emergency_override(db, current_admin, request)


@router.get(
    "/public-key",
    summary="Export public key for offline client verification",
)
async def get_admin_public_key(
    admin_service: AdminServiceDep,
) -> AdminPublicKeyResponse:
    """Export the ClearGuard Admin Ed25519 public key in PEM format."""
    return admin_service.get_public_verification_key()


@router.get(
    "/users",
    summary="List registered ClearGuard client accounts",
)
async def list_admin_users(
    _: CurrentAdminUser,
    db: DbSession,
    admin_service: AdminServiceDep,
    query: Annotated[
        str | None,
        Query(max_length=100, description="Search username or email"),
    ] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> AdminClientListResponse:
    """List client accounts with non-secret vault presence and linked devices."""
    return await admin_service.list_clients(db, query=query, offset=offset, limit=limit)


@router.get(
    "/devices",
    summary="List registered ClearGuard client devices",
)
async def list_admin_devices(
    _: CurrentAdminUser,
    db: DbSession,
    admin_service: AdminServiceDep,
    query: Annotated[
        str | None,
        Query(max_length=100, description="Search device name, identifier, version, or owner"),
    ] = None,
    user_id: Annotated[uuid.UUID | None, Query(description="Filter by owning user ID")] = None,
    is_active: Annotated[bool | None, Query(description="Filter by device active flag")] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> AdminDeviceListResponse:
    """List registered devices across all clients."""
    return await admin_service.list_devices(
        db,
        query=query,
        user_id=user_id,
        is_active=is_active,
        offset=offset,
        limit=limit,
    )
