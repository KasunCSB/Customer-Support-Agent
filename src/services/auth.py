"""
Authentication and OTP verification services.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from src.db import db
from src.logger import get_logger

logger = get_logger(__name__)


def _hash_value(value: str) -> str:
    """SHA256 hash helper."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class AuthService:
    """Handles OTP issuance/validation and session tokens."""

    OTP_EXPIRY_MINUTES = 10
    SESSION_EXPIRY_DAYS = 7

    def __init__(self) -> None:
        pass

    def _get_user_by_email(self, email: str) -> Optional[dict]:
        return db.fetch_one(
            """
            SELECT * FROM users WHERE email = :email AND status = 'active'
            """,
            {"email": email},
        )

    def _get_user_by_phone(self, phone: str) -> Optional[dict]:
        return db.fetch_one(
            """
            SELECT * FROM users WHERE phone_local = :phone AND status = 'active'
            """,
            {"phone": phone},
        )

    def _get_active_verification(self, user_id: str, destination: str) -> Optional[dict]:
        return db.fetch_one(
            """
            SELECT * FROM verifications
            WHERE user_id = :user_id
              AND destination = :destination
              AND verified_at IS NULL
              AND expires_at > NOW()
            ORDER BY created_at DESC
            LIMIT 1
            """,
            {"user_id": user_id, "destination": destination},
        )

    def _issue_otp(self, user: dict, destination: str) -> dict:
        """Create an OTP record and return the code (caller sends)."""
        code = f"{secrets.randbelow(1000000):06d}"
        code_hash = _hash_value(code)
        verification_id = secrets.token_hex(16)
        db.execute(
            """
            INSERT INTO verifications (id, user_id, channel, destination, purpose, code_hash,
                                       expires_at, attempts, max_attempts, verified_at, created_at)
            VALUES (:id, :user_id, 'email', :destination, 'verification', :code_hash,
                    DATE_ADD(NOW(), INTERVAL :ttl MINUTE), 0, 5, NULL, NOW())
            ON DUPLICATE KEY UPDATE
              code_hash = VALUES(code_hash),
              expires_at = VALUES(expires_at),
              attempts = 0,
              verified_at = NULL,
              created_at = NOW()
            """,
            {
                "id": verification_id,
                "user_id": user["id"],
                "destination": destination,
                "code_hash": code_hash,
                "ttl": self.OTP_EXPIRY_MINUTES,
            },
        )

        logger.info("Issued OTP for user %s to %s", user["id"], destination)
        return {
            "user": user,
            "code": code,
            "expires_at": datetime.utcnow() + timedelta(minutes=self.OTP_EXPIRY_MINUTES),
            "verification_id": verification_id,
            "destination": destination,
        }

    def _confirm_otp(self, user: dict, destination: str, code: str) -> dict:
        verification = self._get_active_verification(user["id"], destination)
        if not verification:
            raise ValueError("No active verification. Request a new code.")

        if verification["attempts"] >= verification["max_attempts"]:
            raise ValueError("Maximum attempts exceeded")

        code_hash = _hash_value(code)
        if verification["code_hash"] != code_hash:
            db.execute(
                """
                UPDATE verifications
                SET attempts = attempts + 1
                WHERE id = :id
                """,
                {"id": verification["id"]},
            )
            raise ValueError("Invalid code")

        db.execute(
            """
            UPDATE verifications
            SET verified_at = NOW()
            WHERE id = :id
            """,
            {"id": verification["id"]},
        )

        return self._create_session(user)

    def _create_session(self, user: dict) -> dict:
        session_token = secrets.token_urlsafe(32)
        token_hash = _hash_value(session_token)
        session_id = secrets.token_hex(16)

        db.execute(
            """
            INSERT INTO sessions (id, user_id, token_hash, user_agent, ip_address, expires_at, revoked_at, created_at)
            VALUES (:id, :user_id, :token_hash, '', '', DATE_ADD(NOW(), INTERVAL :ttl DAY), NULL, NOW())
            """,
            {
                "id": session_id,
                "user_id": user["id"],
                "token_hash": token_hash,
                "ttl": self.SESSION_EXPIRY_DAYS,
            },
        )

        logger.info("Created session for user %s", user["id"])
        return {
            "session_token": session_token,
            "session_expires_at": datetime.utcnow() + timedelta(days=self.SESSION_EXPIRY_DAYS),
            "user": {
                "id": user["id"],
                "role": user["role"],
                "email": user["email"],
                "display_name": user["display_name"],
                "phone_local": user.get("phone_local"),
            },
        }

    def start_email_otp(self, email: str) -> dict:
        """Create an OTP record and return the code (caller sends via email)."""
        user = self._get_user_by_email(email)
        if not user:
            raise ValueError("User not found or inactive")
        return self._issue_otp(user, email)

    def confirm_email_otp(self, email: str, code: str) -> dict:
        """Validate OTP and create session token."""
        user = self._get_user_by_email(email)
        if not user:
            raise ValueError("User not found or inactive")
        return self._confirm_otp(user, email, code)

    def start_phone_otp(self, phone: str) -> dict:
        """Create an OTP record for a phone lookup and return the code."""
        user = self._get_user_by_phone(phone)
        if not user:
            raise ValueError("User not found or inactive")
        return self._issue_otp(user, user["email"])

    def confirm_phone_otp(self, phone: str, code: str) -> dict:
        """Validate OTP for a phone lookup and create session token."""
        user = self._get_user_by_phone(phone)
        if not user:
            raise ValueError("User not found or inactive")
        return self._confirm_otp(user, user["email"], code)

    def validate_session(self, token: str) -> Optional[dict]:
        """Validate bearer token and return user record or None."""
        token_hash = _hash_value(token)
        session = db.fetch_one(
            """
            SELECT s.*, u.role, u.email, u.display_name, u.phone_local
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = :token_hash
              AND s.revoked_at IS NULL
              AND s.expires_at > NOW()
            LIMIT 1
            """,
            {"token_hash": token_hash},
        )
        return session
