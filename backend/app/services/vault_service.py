"""Service layer for managing zero-knowledge End-to-End Encrypted (E2EE) User Vaults."""

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vault import UserVault
from app.schemas.vault import VaultResponse, VaultUploadRequest


class VaultService:
    """Manages secure storage of client-side encrypted vault payloads."""

    async def get_vault(self, db: AsyncSession, user_id: uuid.UUID) -> VaultResponse:
        """Fetch the current encrypted vault for the user."""
        result = await db.execute(select(UserVault).where(UserVault.user_id == user_id))
        vault = result.scalar_one_or_none()

        if not vault:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No encrypted vault found for this account",
            )

        return VaultResponse.model_validate(vault)

    async def save_vault(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        req: VaultUploadRequest,
    ) -> VaultResponse:
        """Upsert user's encrypted vault blob, incrementing version."""
        result = await db.execute(select(UserVault).where(UserVault.user_id == user_id))
        vault = result.scalar_one_or_none()

        if vault:
            vault.ciphertext = req.ciphertext
            vault.iv = req.iv
            vault.tag = req.tag
            vault.salt = req.salt
            vault.kdf_iterations = req.kdf_iterations
            vault.vault_version += 1
        else:
            vault = UserVault(
                user_id=user_id,
                ciphertext=req.ciphertext,
                iv=req.iv,
                tag=req.tag,
                salt=req.salt,
                kdf_iterations=req.kdf_iterations,
                vault_version=1,
            )
            db.add(vault)

        await db.commit()
        await db.refresh(vault)
        return VaultResponse.model_validate(vault)


_vault_service: VaultService | None = None


def get_vault_service() -> VaultService:
    """Return VaultService singleton."""
    global _vault_service
    if _vault_service is None:
        _vault_service = VaultService()
    return _vault_service
