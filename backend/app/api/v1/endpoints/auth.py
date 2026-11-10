"""Authentication, token management, and device pairing endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.auth import CurrentUser
from app.core.database import DbSession
from app.schemas.auth import (
    AuthTokensResponse,
    DeviceRegisterRequest,
    DeviceResponse,
    RefreshTokenRequest,
    UserLoginRequest,
    UserProfileResponse,
    UserRegisterRequest,
)
from app.services.auth_service import AuthService, get_auth_service

router = APIRouter(prefix="/auth", tags=["Authentication & Devices"])
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register new user account",
)
async def register(
    request: UserRegisterRequest,
    db: DbSession,
    auth_service: AuthServiceDep,
) -> AuthTokensResponse:
    """Register a new user account with Argon2id password hashing."""
    _, tokens = await auth_service.register_user(db, request)
    return tokens


@router.post(
    "/login",
    summary="Authenticate user and issue tokens",
)
async def login(
    request: UserLoginRequest,
    db: DbSession,
    auth_service: AuthServiceDep,
) -> AuthTokensResponse:
    """Authenticate with username and password, returning access and refresh tokens."""
    _, tokens = await auth_service.login_user(db, request)
    return tokens


@router.post(
    "/refresh",
    summary="Rotate refresh token for new access credentials",
)
async def refresh_token(
    request: RefreshTokenRequest,
    db: DbSession,
    auth_service: AuthServiceDep,
) -> AuthTokensResponse:
    """Exchange an unrevoked, unexpired refresh token for a new token pair."""
    return await auth_service.refresh_tokens(db, request.refresh_token)


@router.post(
    "/devices/register",
    status_code=status.HTTP_201_CREATED,
    summary="Register or update linked client device",
)
async def register_device(
    request: DeviceRegisterRequest,
    current_user: CurrentUser,
    db: DbSession,
    auth_service: AuthServiceDep,
) -> DeviceResponse:
    """Enroll an Android device identifier under the authenticated user account."""
    return await auth_service.register_device(db, current_user.id, request)


@router.get(
    "/me",
    summary="Fetch authenticated user profile and devices",
)
async def get_my_profile(
    current_user: CurrentUser,
    db: DbSession,
) -> UserProfileResponse:
    """Return the profile and active linked devices for the current user."""
    await db.refresh(current_user, ["devices"])
    device_responses = [DeviceResponse.model_validate(d) for d in current_user.devices]

    return UserProfileResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_admin=current_user.is_admin,
        created_at=current_user.created_at,
        devices=device_responses,
    )
