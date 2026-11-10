"""Transactional email and notification dispatch service."""

import logging
from email.message import EmailMessage

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending transactional accountability and verification emails."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def send_partner_verification_email(
        self,
        to_email: str,
        token: str,
        username: str,
        cooloff_days: int = 60,
    ) -> bool:
        """Send verification request email to the trusted partner."""
        verify_url = (
            f"http://{self.settings.app_host}:{self.settings.app_port}"
            f"{self.settings.api_v1_prefix}/accountability/verify-token?token={token}"
        )

        msg = EmailMessage()
        msg["Subject"] = f"ClearGuard Alert: Deactivation Request from {username}"
        msg["From"] = self.settings.smtp_from_email
        msg["To"] = to_email

        body = (
            f"Hello,\n\n"
            f"Your partner '{username}' has requested to deactivate ClearGuard.\n"
            f"A mandatory {cooloff_days}-day cool-off delay has started.\n\n"
            f"As their designated Person of Trust, please review and co-sign this action:\n"
            f"{verify_url}\n\n"
            f"If you did not authorize this, please open the link to reject.\n\n"
            f"— ClearGuard Accountability Team"
        )
        msg.set_content(body)

        logger.info(
            "Dispatching partner verification email to %s for user %s with URL: %s",
            to_email,
            username,
            verify_url,
        )

        # In testing or local environment, log the dispatch
        if self.settings.app_env in ("development", "test"):
            logger.info("Local/Test environment: email recorded in logs successfully.")
            return True

        # In production, attempt actual SMTP dispatch
        try:
            import aiosmtplib

            await aiosmtplib.send(
                msg,
                hostname=self.settings.smtp_host,
                port=self.settings.smtp_port,
                username=self.settings.smtp_user or None,
                password=self.settings.smtp_password or None,
                use_tls=self.settings.smtp_port == 465,
                start_tls=self.settings.smtp_port == 587,
            )
            return True
        except Exception as exc:
            logger.warning("Failed to dispatch partner email via SMTP: %s", exc)
            return False


_email_service: EmailService | None = None


def get_email_service() -> EmailService:
    """Return EmailService instance."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
