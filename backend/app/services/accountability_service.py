"""Service layer for multi-factor accountability, partner co-signing, and 60-day delay."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import generate_secure_token, hash_token
from app.models.accountability import DeactivationRequest, DeactivationStatus
from app.models.user import User
from app.schemas.accountability import (
    DeactivationInitiateRequest,
    DeactivationStatusResponse,
    PartnerCosignRequest,
    PartnerVerifyTokenResponse,
)
from app.services.email_service import EmailService, get_email_service


class AccountabilityService:
    """Manages high-friction deactivation workflows and partner verification."""

    def __init__(self, email_service: EmailService | None = None) -> None:
        self.email_service = email_service or get_email_service()

    async def initiate_deactivation(
        self,
        db: AsyncSession,
        user: User,
        req: DeactivationInitiateRequest,
    ) -> DeactivationStatusResponse:
        """Initiate deactivation, start 60-day countdown, and send email to partner."""
        # 1. Check if there is already an active (pending, approved) deactivation request
        result = await db.execute(
            select(DeactivationRequest).where(
                DeactivationRequest.user_id == user.id,
                DeactivationRequest.status.in_(
                    [
                        DeactivationStatus.PENDING_PARTNER_APPROVAL.value,
                        DeactivationStatus.PARTNER_APPROVED.value,
                    ]
                ),
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            return self._build_status_response(existing)

        # 2. Generate secure one-time partner token
        raw_token = generate_secure_token(32)
        token_hash_val = hash_token(raw_token)
        now = datetime.now(UTC)
        expires_at = now + timedelta(days=7)  # 7-day token window

        deact = DeactivationRequest(
            user_id=user.id,
            device_id=req.device_id,
            partner_email=str(req.partner_email),
            started_at=now,
            cooloff_days=60,
            status=DeactivationStatus.PENDING_PARTNER_APPROVAL.value,
            partner_token_hash=token_hash_val,
            partner_token_expires_at=expires_at,
        )
        db.add(deact)
        await db.commit()
        await db.refresh(deact)

        # 3. Dispatch transactional email to partner
        await self.email_service.send_partner_verification_email(
            to_email=str(req.partner_email),
            token=raw_token,
            username=user.username,
            cooloff_days=60,
        )

        return self._build_status_response(deact)

    async def get_deactivation_status(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> DeactivationStatusResponse:
        """Fetch the latest active deactivation request for the user."""
        result = await db.execute(
            select(DeactivationRequest)
            .where(DeactivationRequest.user_id == user_id)
            .order_by(DeactivationRequest.created_at.desc())
        )
        deact = result.scalars().first()

        if not deact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No deactivation request found for this account",
            )

        return self._build_status_response(deact)

    async def cancel_deactivation(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> DeactivationStatusResponse:
        """Cancel active deactivation countdown."""
        result = await db.execute(
            select(DeactivationRequest).where(
                DeactivationRequest.user_id == user_id,
                DeactivationRequest.status.in_(
                    [
                        DeactivationStatus.PENDING_PARTNER_APPROVAL.value,
                        DeactivationStatus.PARTNER_APPROVED.value,
                    ]
                ),
            )
        )
        deact = result.scalar_one_or_none()

        if not deact:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active deactivation request available to cancel",
            )

        deact.status = DeactivationStatus.CANCELLED.value
        await db.commit()
        await db.refresh(deact)
        return self._build_status_response(deact)

    async def verify_partner_token(
        self,
        db: AsyncSession,
        raw_token: str,
    ) -> PartnerVerifyTokenResponse:
        """Validate a partner verification token from an email link."""
        token_hash_val = hash_token(raw_token)
        now = datetime.now(UTC)

        result = await db.execute(
            select(DeactivationRequest).where(
                DeactivationRequest.partner_token_hash == token_hash_val
            )
        )
        deact = result.scalar_one_or_none()

        if not deact:
            return PartnerVerifyTokenResponse(
                valid=False,
                message="Invalid or unrecognized partner verification token",
            )

        if deact.partner_token_expires_at < now:
            return PartnerVerifyTokenResponse(
                valid=False,
                message="This partner verification token has expired",
            )

        if deact.status == DeactivationStatus.CANCELLED.value:
            return PartnerVerifyTokenResponse(
                valid=False,
                message="The user has already cancelled this deactivation request",
            )

        return PartnerVerifyTokenResponse(
            valid=True,
            request_id=deact.id,
            started_at=deact.started_at,
            cooloff_days=deact.cooloff_days,
            status=deact.status,
            message="Partner verification token is active and valid",
        )

    async def partner_cosign(
        self,
        db: AsyncSession,
        req: PartnerCosignRequest,
    ) -> PartnerVerifyTokenResponse:
        """Process partner's approval or rejection decision."""
        token_hash_val = hash_token(req.token)
        now = datetime.now(UTC)

        result = await db.execute(
            select(DeactivationRequest).where(
                DeactivationRequest.partner_token_hash == token_hash_val
            )
        )
        deact = result.scalar_one_or_none()

        if not deact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid verification token",
            )

        if deact.status != DeactivationStatus.PENDING_PARTNER_APPROVAL.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Request is not pending partner approval (status: {deact.status})",
            )

        deact.partner_responded_at = now
        if req.decision == "approve":
            deact.status = DeactivationStatus.PARTNER_APPROVED.value
            msg = (
                "Deactivation request has been successfully co-signed and approved by the partner."
            )
        else:
            deact.status = DeactivationStatus.PARTNER_REJECTED.value
            deact.partner_rejection_reason = req.rejection_reason
            msg = (
                "Deactivation request has been rejected by the partner. Protection remains active."
            )

        await db.commit()
        await db.refresh(deact)

        return PartnerVerifyTokenResponse(
            valid=True,
            request_id=deact.id,
            started_at=deact.started_at,
            cooloff_days=deact.cooloff_days,
            status=deact.status,
            message=msg,
        )

    def _build_status_response(self, deact: DeactivationRequest) -> DeactivationStatusResponse:
        """Compute countdown metrics and assemble response."""
        now = datetime.now(UTC)
        started = deact.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=UTC)

        end_time = started + timedelta(days=deact.cooloff_days)
        remaining_seconds = max(0, int((end_time - now).total_seconds()))
        remaining_days = max(0, int((remaining_seconds + 86399) // 86400))

        can_cancel = deact.status in (
            DeactivationStatus.PENDING_PARTNER_APPROVAL.value,
            DeactivationStatus.PARTNER_APPROVED.value,
        )

        return DeactivationStatusResponse(
            request_id=deact.id,
            user_id=deact.user_id,
            partner_email=deact.partner_email,
            started_at=started,
            cooloff_days=deact.cooloff_days,
            days_remaining=remaining_days,
            seconds_remaining=remaining_seconds,
            status=deact.status,
            can_cancel=can_cancel,
            partner_responded_at=deact.partner_responded_at,
        )


_accountability_service: AccountabilityService | None = None


def get_accountability_service() -> AccountabilityService:
    """Return AccountabilityService instance."""
    global _accountability_service
    if _accountability_service is None:
        _accountability_service = AccountabilityService()
    return _accountability_service
