"""
Simple SMTP email client for sending OTPs and notifications.

If email is not configured, the client will log the OTP instead of sending.
"""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from src.config import settings
from src.logger import get_logger

logger = get_logger(__name__)


class EmailClient:
    """SMTP email sender with graceful fallback to logging."""

    def __init__(self) -> None:
        self.config = settings.email

    def send(self, to_email: str, subject: str, body: str) -> None:
        """Send an email or log if SMTP is not configured."""
        if not self.config.is_configured:
            logger.warning("Email not configured; logging email instead")
            logger.info("Email to %s | %s | %s", to_email, subject, body)
            return

        msg = EmailMessage()
        # Include display name if provided
        msg["From"] = formataddr((self.config.sender_name, self.config.sender))
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)

        try:
            if self.config.use_tls:
                with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                    server.starttls()
                    server.login(self.config.smtp_username, self.config.smtp_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                    server.login(self.config.smtp_username, self.config.smtp_password)
                    server.send_message(msg)
            logger.info("Sent email to %s", to_email)
        except Exception as exc:  # pylint: disable=broad-except
            logger.error("Failed to send email: %s", exc)
            raise
