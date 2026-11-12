"""Service layer for ClearGuard Admin emergency early deactivation override."""

import json
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.crypto import CryptoManager, get_crypto_manager
from app.models.accountability import AdminOverride, DeactivationRequest, DeactivationStatus
from app.models.user import Device, User
from app.schemas.admin import (
    AdminClientItem,
    AdminClientListResponse,
    AdminDeviceItem,
    AdminDeviceListResponse,
    AdminOverrideCreateRequest,
    AdminOverrideResponse,
    AdminPendingRequestItem,
    AdminPublicKeyResponse,
)
from app.schemas.auth import DeviceResponse


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

    async def list_clients(
        self,
        db: AsyncSession,
        query: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> AdminClientListResponse:
        """List registered client accounts with non-secret vault and device summaries."""
        filters = []
        if query and query.strip():
            pattern = f"%{query.strip()}%"
            filters.append(or_(User.username.ilike(pattern), User.email.ilike(pattern)))

        count_stmt = select(func.count()).select_from(User)
        if filters:
            count_stmt = count_stmt.where(*filters)
        total = int((await db.scalar(count_stmt)) or 0)

        stmt = (
            select(User)
            .options(
                selectinload(User.devices),
                selectinload(User.vault),
                selectinload(User.deactivation_requests),
            )
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if filters:
            stmt = stmt.where(*filters)

        users = (await db.execute(stmt)).scalars().all()

        items: list[AdminClientItem] = []
        for user in users:
            sorted_devices = sorted(user.devices, key=lambda d: d.last_seen_at, reverse=True)
            latest_deact = (
                max(user.deactivation_requests, key=lambda r: r.created_at)
                if user.deactivation_requests
                else None
            )
            items.append(
                AdminClientItem(
                    id=user.id,
                    username=user.username,
                    email=user.email,
                    is_active=user.is_active,
                    is_admin=user.is_admin,
                    created_at=user.created_at,
                    updated_at=user.updated_at,
                    device_count=len(sorted_devices),
                    has_vault=user.vault is not None,
                    vault_version=user.vault.vault_version if user.vault else None,
                    vault_updated_at=user.vault.updated_at if user.vault else None,
                    latest_deactivation_status=latest_deact.status if latest_deact else None,
                    devices=[DeviceResponse.model_validate(d) for d in sorted_devices],
                )
            )

        return AdminClientListResponse.create(
            items=items,
            total=total,
            offset=offset,
            limit=limit,
        )

    async def list_devices(
        self,
        db: AsyncSession,
        query: str | None = None,
        user_id: uuid.UUID | None = None,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> AdminDeviceListResponse:
        """List registered client devices joined with their owning user identity."""
        filters = []
        if user_id is not None:
            filters.append(Device.user_id == user_id)
        if is_active is not None:
            filters.append(Device.is_active == is_active)
        if query and query.strip():
            pattern = f"%{query.strip()}%"
            filters.append(
                or_(
                    Device.device_name.ilike(pattern),
                    Device.device_identifier.ilike(pattern),
                    Device.client_version.ilike(pattern),
                    User.username.ilike(pattern),
                    User.email.ilike(pattern),
                )
            )

        count_stmt = select(func.count()).select_from(Device).join(User, Device.user_id == User.id)
        if filters:
            count_stmt = count_stmt.where(*filters)
        total = int((await db.scalar(count_stmt)) or 0)

        stmt = (
            select(Device, User.username, User.email)
            .join(User, Device.user_id == User.id)
            .order_by(Device.last_seen_at.desc())
            .offset(offset)
            .limit(limit)
        )
        if filters:
            stmt = stmt.where(*filters)

        rows = (await db.execute(stmt)).all()
        items = [
            AdminDeviceItem(
                id=device.id,
                user_id=device.user_id,
                username=username,
                email=email,
                device_identifier=device.device_identifier,
                device_name=device.device_name,
                client_version=device.client_version,
                is_active=device.is_active,
                last_seen_at=device.last_seen_at,
                created_at=device.created_at,
            )
            for device, username, email in rows
        ]

        return AdminDeviceListResponse.create(
            items=items,
            total=total,
            offset=offset,
            limit=limit,
        )


_admin_service: AdminService | None = None


def get_admin_service() -> AdminService:
    """Return AdminService instance."""
    global _admin_service
    if _admin_service is None:
        _admin_service = AdminService()
    return _admin_service
