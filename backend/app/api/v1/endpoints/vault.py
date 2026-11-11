"""End-to-End Encrypted (E2EE) User Vault API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.auth import CurrentUser
from app.core.database import DbSession
from app.schemas.vault import VaultResponse, VaultUploadRequest
from app.services.vault_service import VaultService, get_vault_service

router = APIRouter(prefix="/vault", tags=["E2EE User Vault"])
VaultServiceDep = Annotated[VaultService, Depends(get_vault_service)]


@router.get(
    "",
    summary="Retrieve client-side encrypted vault blob",
)
async def get_vault(
    current_user: CurrentUser,
    db: DbSession,
    vault_service: VaultServiceDep,
) -> VaultResponse:
    """Retrieve the authenticated user's zero-knowledge encrypted vault.

    The backend stores only ciphertext and IV; decryption is performed
    strictly on the client device using the user's master key.
    """
    return await vault_service.get_vault(db, current_user.id)


@router.put(
    "",
    status_code=status.HTTP_200_OK,
    summary="Synchronize client-side encrypted vault blob",
)
async def upload_vault(
    request: VaultUploadRequest,
    current_user: CurrentUser,
    db: DbSession,
    vault_service: VaultServiceDep,
) -> VaultResponse:
    """Upsert the user's client-side encrypted vault record."""
    return await vault_service.save_vault(db, current_user.id, request)
