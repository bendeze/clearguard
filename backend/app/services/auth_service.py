"""Service layer for user registration, authentication, tokens, and devices."""

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    create_access_token,
    generate_secure_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.core.config import Settings, get_settings
from app.models.user import Device, RefreshToken, User
from app.schemas.auth import (
    AuthTokensResponse,
    DeviceRegisterRequest,
    DeviceResponse,
    UserLoginRequest,
    UserRegisterRequest,
)


class AuthService:
    """Manages user authentication, device pairing, and token issuance."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def register_user(
        self,
        db: AsyncSession,
        req: UserRegisterRequest,
    ) -> tuple[User, AuthTokensResponse]:
        """Register a new user account with Argon2id password hashing."""
        # 1. Check duplicate username
        existing_username = await db.scalar(select(User).where(User.username == req.username))
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username is already taken",
            )

        # 2. Check duplicate email if provided
        if req.email:
            existing_email = await db.scalar(select(User).where(User.email == req.email))
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email is already registered",
                )

        # 3. Create user
        user = User(
            username=req.username,
            hashed_password=hash_password(req.password),
            email=req.email,
            is_active=True,
            is_admin=False,
        )
        db.add(user)
        await db.flush()

        # 4. Issue tokens
        tokens = await self._issue_tokens(db, user)
        await db.commit()
        await db.refresh(user)
        return user, tokens

    async def login_user(
        self,
        db: AsyncSession,
        req: UserLoginRequest,
    ) -> tuple[User, AuthTokensResponse]:
        """Authenticate user credentials and issue token pair."""
        result = await db.execute(select(User).where(User.username == req.username))
        user = result.scalar_one_or_none()

        if not user or not verify_password(req.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated",
            )

        # Register or update device if provided
        device_id: uuid.UUID | None = None
        if req.device_identifier:
            device = await self._get_or_create_device(
                db,
                user.id,
                req.device_identifier,
                req.device_name or "Android Device",
            )
            device_id = device.id

        tokens = await self._issue_tokens(db, user, device_id=device_id)
        await db.commit()
        return user, tokens

    async def refresh_tokens(
        self,
        db: AsyncSession,
        refresh_token_secret: str,
    ) -> AuthTokensResponse:
        """Rotate a refresh token and issue new credentials."""
        token_hash_val = hash_token(refresh_token_secret)
        now = datetime.now(UTC)

        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash_val,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > now,
            )
        )
        stored_token = result.scalar_one_or_none()

        if not stored_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Revoke used token (Token Rotation)
        stored_token.revoked_at = now

        # Fetch associated user
        user = await db.get(User, stored_token.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is invalid or inactive",
            )

        # Issue new token pair
        tokens = await self._issue_tokens(db, user, device_id=stored_token.device_id)
        await db.commit()
        return tokens

    async def register_device(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        req: DeviceRegisterRequest,
    ) -> DeviceResponse:
        """Register or update an Android device under the authenticated account."""
        device = await self._get_or_create_device(
            db,
            user_id,
            req.device_identifier,
            req.device_name,
            req.client_version,
        )
        await db.commit()
        await db.refresh(device)
        return DeviceResponse.model_validate(device)

    async def _issue_tokens(
        self,
        db: AsyncSession,
        user: User,
        device_id: uuid.UUID | None = None,
    ) -> AuthTokensResponse:
        """Issue access and refresh token pair."""
        access_token = create_access_token(
            user_id=user.id,
            username=user.username,
            device_id=device_id,
            is_admin=user.is_admin,
            settings=self.settings,
        )

        refresh_secret = generate_secure_token(32)
        refresh_hash = hash_token(refresh_secret)
        expires_at = datetime.now(UTC) + timedelta(days=self.settings.refresh_token_expire_days)

        refresh_record = RefreshToken(
            user_id=user.id,
            device_id=device_id,
            token_hash=refresh_hash,
            expires_at=expires_at,
        )
        db.add(refresh_record)

        return AuthTokensResponse(
            access_token=access_token,
            refresh_token=refresh_secret,
            token_type="bearer",
            expires_in=self.settings.access_token_expire_minutes * 60,
        )

    async def _get_or_create_device(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        device_identifier: str,
        device_name: str = "Android Device",
        client_version: str = "0.7.0",
    ) -> Device:
        """Fetch existing device or create a new one."""
        result = await db.execute(
            select(Device).where(
                Device.user_id == user_id,
                Device.device_identifier == device_identifier,
            )
        )
        device = result.scalar_one_or_none()

        now = datetime.now(UTC)
        if device:
            device.device_name = device_name
            device.client_version = client_version
            device.last_seen_at = now
            device.is_active = True
        else:
            device = Device(
                user_id=user_id,
                device_identifier=device_identifier,
                device_name=device_name,
                client_version=client_version,
                is_active=True,
                last_seen_at=now,
            )
            db.add(device)
            await db.flush()

        return device


_auth_service: AuthService | None = None


def get_auth_service() -> AuthService:
    """Return AuthService instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
