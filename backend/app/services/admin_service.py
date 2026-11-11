"""Service layer for ClearGuard Admin emergency early deactivation override."""

import json
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import CryptoManager, get_crypto_manager
from app.models.accountability import AdminOverride, DeactivationRequest, DeactivationStatus
from app.models.user import User
from app.schemas.admin import (
    AdminOverrideCreateRequest,
    AdminOverrideResponse,
    AdminPendingRequestItem,
    AdminPublicKeyResponse,
)


class AdminService:
    """Manages emergency override authorization and cryptographic token issuance."""

    def __init__(self, crypto_manager: CryptoManager | None = None) -> None:
        self.crypto_manager = crypto_manager or get_crypto_manager()

    async def list_pending_requests(
        self,
        db: AsyncSession,
    ) -> list[AdminPendingRequestItem]:
        """List all active deactivation requests pending review on the admin console."""
        stmt = (
            select(DeactivationRequest, User.username)
            .join(User, DeactivationRequest.user_id == User.id)
            .where(
                DeactivationRequest.status.in_(
                    [
                        DeactivationStatus.PENDING_PARTNER_APPROVAL.value,
                        DeactivationStatus.PARTNER_APPROVED.value,
                    ]
                )
            )
            .order_by(DeactivationRequest.started_at.desc())
        )
        result = await db.execute(stmt)
        rows = result.all()

        items: list[AdminPendingRequestItem] = []
        for deact, uname in rows:
            started = deact.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=UTC)

            items.append(
                AdminPendingRequestItem(
                    request_id=deact.id,
                    user_id=deact.user_id,
                    username=uname,
                    partner_email=deact.partner_email,
                    started_at=started,
                    cooloff_days=deact.cooloff_days,
                    status=deact.status,
                )
            )
        return items

    async def approve_emergency_override(
        self,
        db: AsyncSession,
        admin_user: User,
        req: AdminOverrideCreateRequest,
    ) -> AdminOverrideResponse:
        """Issue an asymmetrically signed Ed25519 token permitting immediate deactivation."""
        result = await db.execute(
            select(DeactivationRequest).where(DeactivationRequest.id == req.request_id)
        )
        deact = result.scalar_one_or_none()

        if not deact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deactivation request not found",
            )

        now = datetime.now(UTC)

        # Build auditable payload for asymmetric signing
        override_payload = {
            "request_id": str(deact.id),
            "user_id": str(deact.user_id),
            "device_id": str(deact.device_id) if deact.device_id else None,
            "action": "emergency_deactivate_override",
            "issued_at": int(now.timestamp()),
            "reason": req.reason,
            "admin_id": str(admin_user.id),
        }
        payload_bytes = json.dumps(override_payload, sort_keys=True).encode("utf-8")
        signature_b64 = self.crypto_manager.sign_bytes(payload_bytes)

        # Composite signed token combining payload and signature
        composite_token = json.dumps(
            {
                "payload": override_payload,
                "signature": signature_b64,
            }
        )

        override = AdminOverride(
            request_id=deact.id,
            admin_user_id=admin_user.id,
            reason=req.reason,
            signed_token=composite_token,
            issued_at=now,
        )
        db.add(override)

        # Update deactivation request state
        deact.status = DeactivationStatus.ADMIN_OVERRIDDEN.value

        await db.commit()
        await db.refresh(override)

        return AdminOverrideResponse(
            override_id=override.id,
            request_id=override.request_id,
            reason=override.reason,
            signed_token=override.signed_token,
            issued_at=override.issued_at,
        )

    async def reject_emergency_override(
        self,
        db: AsyncSession,
        request_id: uuid.UUID,
    ) -> None:
        """Reject an emergency override, returning status to normal countdown."""
        result = await db.execute(
            select(DeactivationRequest).where(DeactivationRequest.id == request_id)
        )
        deact = result.scalar_one_or_none()
        if not deact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Deactivation request not found",
            )
        # Does not override, keeps request in its previous status or active
        await db.commit()

    def get_public_verification_key(self) -> AdminPublicKeyResponse:
        """Return the public key in PEM format for offline client verification."""
        pem = self.crypto_manager.get_public_key_pem()
        return AdminPublicKeyResponse(public_key_pem=pem, algorithm="Ed25519")


_admin_service: AdminService | None = None


def get_admin_service() -> AdminService:
    """Return AdminService instance."""
    global _admin_service
    if _admin_service is None:
        _admin_service = AdminService()
    return _admin_service
