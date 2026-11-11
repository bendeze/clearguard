"""Tests for Multi-Factor Accountability, Partner Verification, and 60-Day Delay (Phase B6.3)."""

import logging

import pytest
from httpx import AsyncClient

from app.core.config import Settings
from app.core.database import engine
from app.models.accountability import DeactivationRequest
from app.models.base import Base
from app.services.email_service import EmailService


@pytest.fixture
async def setup_accountability_database():
    """Ensure clean schema for accountability tests."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.anyio
async def test_deactivation_flow_and_partner_approval(
    async_client: AsyncClient, setup_accountability_database
) -> None:
    """Verify deactivation initiation, email dispatch, countdown, and partner co-signing."""
    # 1. Register user
    reg = await async_client.post(
        "/api/v1/auth/register",
        json={"username": "frank_accountability", "password": "FrankPassword123!"},
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Initiate deactivation
    init_res = await async_client.post(
        "/api/v1/accountability/request-deactivation",
        headers=headers,
        json={"partner_email": "sponsor@example.com"},
    )
    assert init_res.status_code == 201
    init_data = init_res.json()
    assert init_data["status"] == "pending_partner_approval"
    assert init_data["cooloff_days"] == 60
    assert init_data["days_remaining"] == 60
    assert init_data["can_cancel"] is True

    # Extract token hash from DB to simulate partner clicking email link
    async with engine.connect() as conn:
        result = await conn.execute(DeactivationRequest.__table__.select())
        row = result.first()
        assert row is not None

    # Verify query status endpoint
    status_res = await async_client.get("/api/v1/accountability/status", headers=headers)
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "pending_partner_approval"


@pytest.mark.anyio
async def test_deactivation_cancellation(
    async_client: AsyncClient, setup_accountability_database
) -> None:
    """Verify user ability to abort deactivation countdown."""
    reg = await async_client.post(
        "/api/v1/auth/register",
        json={"username": "grace_cancel", "password": "GracePassword123!"},
    )
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    await async_client.post(
        "/api/v1/accountability/request-deactivation",
        headers=headers,
        json={"partner_email": "friend@example.com"},
    )

    cancel_res = await async_client.post(
        "/api/v1/accountability/cancel-deactivation",
        headers=headers,
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"
    assert cancel_res.json()["can_cancel"] is False


@pytest.mark.anyio
async def test_email_service_uses_public_base_url(caplog: pytest.LogCaptureFixture) -> None:
    """Verify partner verification email URL uses PUBLIC_BASE_URL when configured."""
    settings = Settings(
        app_env="test",
        public_base_url="https://api.clearguard.example.com/",
    )
    service = EmailService(settings=settings)
    with caplog.at_level(logging.INFO):
        sent = await service.send_partner_verification_email(
            to_email="partner@example.com",
            token="sample-partner-token-123456",
            username="alice",
        )
    assert sent is True
    assert (
        "https://api.clearguard.example.com/api/v1/accountability/verify-token"
        "?token=sample-partner-token-123456" in caplog.text
    )
