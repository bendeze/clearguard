"""Multi-factor accountability, partner co-signing, and 60-day delay endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.auth import CurrentUser
from app.core.database import DbSession
from app.schemas.accountability import (
    DeactivationInitiateRequest,
    DeactivationStatusResponse,
    PartnerCosignRequest,
    PartnerVerifyTokenResponse,
)
from app.services.accountability_service import (
    AccountabilityService,
    get_accountability_service,
)

router = APIRouter(prefix="/accountability", tags=["Multi-Factor Accountability"])
AccountabilityServiceDep = Annotated[AccountabilityService, Depends(get_accountability_service)]


@router.post(
    "/request-deactivation",
    status_code=status.HTTP_201_CREATED,
    summary="Initiate 60-day deactivation process with partner notification",
)
async def request_deactivation(
    request: DeactivationInitiateRequest,
    current_user: CurrentUser,
    db: DbSession,
    service: AccountabilityServiceDep,
) -> DeactivationStatusResponse:
    """Start the mandatory 60-day countdown and notify the designated partner."""
    return await service.initiate_deactivation(db, current_user, request)


@router.get(
    "/status",
    summary="Retrieve active deactivation countdown and status",
)
async def get_deactivation_status(
    current_user: CurrentUser,
    db: DbSession,
    service: AccountabilityServiceDep,
) -> DeactivationStatusResponse:
    """Fetch live deactivation countdown metrics and partner approval state."""
    return await service.get_deactivation_status(db, current_user.id)


@router.post(
    "/cancel-deactivation",
    summary="Cancel active deactivation request",
)
async def cancel_deactivation(
    current_user: CurrentUser,
    db: DbSession,
    service: AccountabilityServiceDep,
) -> DeactivationStatusResponse:
    """Abort an active deactivation countdown, maintaining protection."""
    return await service.cancel_deactivation(db, current_user.id)


@router.get(
    "/verify-token",
    summary="Validate partner verification token from email link",
)
async def verify_partner_token(
    token: Annotated[str, Query(min_length=16, description="One-time partner verification token")],
    db: DbSession,
    service: AccountabilityServiceDep,
) -> PartnerVerifyTokenResponse:
    """Public web endpoint to validate a partner verification token."""
    return await service.verify_partner_token(db, token)


@router.post(
    "/partner-cosign",
    summary="Submit partner co-signing approval or rejection decision",
)
async def partner_cosign(
    request: PartnerCosignRequest,
    db: DbSession,
    service: AccountabilityServiceDep,
) -> PartnerVerifyTokenResponse:
    """Public web endpoint for the trusted partner to approve or reject deactivation."""
    return await service.partner_cosign(db, request)
