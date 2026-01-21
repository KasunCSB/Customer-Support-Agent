"""
Action service: create tickets and manage subscriptions.
"""

from __future__ import annotations

import secrets
from typing import Optional, Tuple

from src.db import db
from src.logger import get_logger

logger = get_logger(__name__)


def _write_audit(actor_id: str, actor_role: str, action: str, target_type: Optional[str], target_id: Optional[str], request_payload: dict, response_payload: dict, severity: str = "info") -> None:
    """Record an audit log entry."""
    db.execute(
        """
        INSERT INTO audit_logs (id, actor_id, actor_role, action, target_type, target_id, request, response, severity, created_at)
        VALUES (:id, :actor_id, :actor_role, :action, :target_type, :target_id, :request, :response, :severity, NOW())
        """,
        {
            "id": secrets.token_hex(16),
            "actor_id": actor_id,
            "actor_role": actor_role,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "request": request_payload,
            "response": response_payload,
            "severity": severity,
        },
    )


class ActionService:
    """Implements business actions backed by the database."""

    def __init__(self) -> None:
        pass

    def _get_user_by_id(self, user_id: str) -> Optional[dict]:
        return db.fetch_one(
            "SELECT * FROM users WHERE id = :id AND status = 'active' LIMIT 1",
            {"id": user_id},
        )

    def _get_user_by_email_or_phone(self, email: Optional[str], phone: Optional[str]) -> Optional[dict]:
        if email:
            user = db.fetch_one(
                "SELECT * FROM users WHERE email = :email AND status = 'active' LIMIT 1",
                {"email": email},
            )
            if user:
                return user
        if phone:
            user = db.fetch_one(
                "SELECT * FROM users WHERE phone_e164 = :phone AND status = 'active' LIMIT 1",
                {"phone": phone},
            )
            if user:
                return user
        return None

    def _get_service_by_code(self, code: str) -> Optional[dict]:
        return db.fetch_one(
            "SELECT * FROM services WHERE code = :code",
            {"code": code},
        )

    def get_balance(self, *, user_id: str) -> dict:
        user = self._get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        metadata = user.get("metadata") or {}
        balance = None
        if isinstance(metadata, dict):
            balance = metadata.get("balance_lkr") or metadata.get("balance")
        return {
            "status": "available" if balance is not None else "unavailable",
            "balance_lkr": balance,
        }

    def list_services(self, *, limit: int = 6) -> list:
        return db.fetch_all(
            """
            SELECT id, code, name, category, price, currency, validity_days
            FROM services
            ORDER BY price ASC
            LIMIT :limit
            """,
            {"limit": limit},
        )

    def list_active_subscriptions_by_user_id(self, *, user_id: str) -> list:
        return db.fetch_all(
            """
            SELECT s.id, sv.code, sv.name, s.status, s.activated_at, s.expires_at
            FROM subscriptions s
            JOIN services sv ON sv.id = s.service_id
            WHERE s.user_id = :user_id AND s.status = 'active'
            ORDER BY s.updated_at DESC
            """,
            {"user_id": user_id},
        )

    def list_available_services_by_user_id(self, *, user_id: str, limit: int = 6) -> list:
        return db.fetch_all(
            """
            SELECT sv.id, sv.code, sv.name, sv.category, sv.price, sv.currency, sv.validity_days
            FROM services sv
            LEFT JOIN subscriptions s
              ON s.service_id = sv.id
             AND s.user_id = :user_id
             AND s.status = 'active'
            WHERE s.id IS NULL
            ORDER BY sv.price ASC
            LIMIT :limit
            """,
            {"user_id": user_id, "limit": limit},
        )

    def create_ticket(self, *, actor_id: str, actor_role: str, user_email: Optional[str], user_phone: Optional[str], subject: str, description: str, priority: str = "normal", idempotency_key: Optional[str] = None) -> dict:
        user = self._get_user_by_email_or_phone(user_email, user_phone)
        if not user:
            raise ValueError("User not found")

        # Idempotency check
        if idempotency_key:
            existing = db.fetch_one(
                """
                SELECT result FROM actions
                WHERE idempotency_key = :key AND action_name = 'create_ticket' AND status = 'completed'
                """,
                {"key": idempotency_key},
            )
            if existing and existing.get("result"):
                return existing["result"]

        ticket_id = secrets.token_hex(16)
        external_id = f"TICK-{secrets.randbelow(9000)+1000}"

        db.execute(
            """
            INSERT INTO tickets (id, external_id, user_id, subject, description, priority, status, assigned_to, metadata, created_at)
            VALUES (:id, :external_id, :user_id, :subject, :description, :priority, 'open', NULL, JSON_OBJECT('channel','chat'), NOW())
            """,
            {
                "id": ticket_id,
                "external_id": external_id,
                "user_id": user["id"],
                "subject": subject,
                "description": description,
                "priority": priority,
            },
        )

        db.execute(
            """
            INSERT INTO ticket_events (id, ticket_id, event_type, actor_id, payload, created_at)
            VALUES (:id, :ticket_id, 'created', :actor_id, JSON_OBJECT('note','Created via API'), NOW())
            """,
            {
                "id": secrets.token_hex(16),
                "ticket_id": ticket_id,
                "actor_id": user["id"],
            },
        )

        # Persist action record for idempotency/audit
        action_id = secrets.token_hex(16)
        db.execute(
            """
            INSERT INTO actions (id, idempotency_key, session_id, user_id, action_name, status, requires_confirmation, params, result, created_at, completed_at)
            VALUES (:id, :idem, NULL, :user_id, 'create_ticket', 'completed', 0, :params, :result, NOW(), NOW())
            """,
            {
                "id": action_id,
                "idem": idempotency_key or f"auto-{action_id}",
                "user_id": user["id"],
                "params": {"subject": subject, "description": description, "priority": priority},
                "result": {"ticket_id": external_id, "status": "open"},
            },
        )

        _write_audit(actor_id, actor_role, "create_ticket", "ticket", ticket_id, {"subject": subject}, {"ticket_id": external_id})
        logger.info("Created ticket %s for user %s", external_id, user["id"])
        return {
            "ticket_id": external_id,
            "status": "open",
        }

    def activate_service(self, *, actor_id: str, actor_role: str, user_email: Optional[str], user_phone: Optional[str], service_code: str, idempotency_key: Optional[str] = None) -> dict:
        user = self._get_user_by_email_or_phone(user_email, user_phone)
        if not user:
            raise ValueError("User not found")
        service = self._get_service_by_code(service_code)
        if not service:
            raise ValueError("Service not found")

        if idempotency_key:
            existing = db.fetch_one(
                """
                SELECT result FROM actions
                WHERE idempotency_key = :key AND action_name = 'activate_service' AND status = 'completed'
                """,
                {"key": idempotency_key},
            )
            if existing and existing.get("result"):
                return existing["result"]

        existing = db.fetch_one(
            """
            SELECT * FROM subscriptions
            WHERE user_id = :user_id AND service_id = :service_id
            """,
            {"user_id": user["id"], "service_id": service["id"]},
        )

        if existing and existing["status"] == "active":
            return {"status": "already_active"}

        subscription_id = existing["id"] if existing else secrets.token_hex(16)
        db.execute(
            """
            INSERT INTO subscriptions (id, user_id, service_id, status, activated_at, expires_at, external_ref, metadata, created_at, updated_at)
            VALUES (:id, :user_id, :service_id, 'active', NOW(), DATE_ADD(NOW(), INTERVAL 30 DAY), :external_ref, JSON_OBJECT('channel','chat'), NOW(), NOW())
            ON DUPLICATE KEY UPDATE
              status = 'active',
              activated_at = NOW(),
              expires_at = DATE_ADD(NOW(), INTERVAL 30 DAY),
              metadata = JSON_SET(IFNULL(metadata, JSON_OBJECT()), '$.channel', 'chat'),
              updated_at = NOW()
            """,
            {
                "id": subscription_id,
                "user_id": user["id"],
                "service_id": service["id"],
                "external_ref": f"prov-{secrets.randbelow(9000)+1000}",
            },
        )

        action_id = secrets.token_hex(16)
        db.execute(
            """
            INSERT INTO actions (id, idempotency_key, session_id, user_id, action_name, status, requires_confirmation, params, result, created_at, completed_at)
            VALUES (:id, :idem, NULL, :user_id, 'activate_service', 'completed', 0, :params, :result, NOW(), NOW())
            """,
            {
                "id": action_id,
                "idem": idempotency_key or f"auto-{action_id}",
                "user_id": user["id"],
                "params": {"service_code": service_code},
                "result": {"status": "activated", "service_code": service_code},
            },
        )

        _write_audit(actor_id, actor_role, "activate_service", "subscription", subscription_id, {"service_code": service_code}, {"status": "activated"})
        logger.info("Activated %s for user %s", service_code, user["id"])
        return {
            "status": "activated",
            "service_code": service_code,
        }

    def deactivate_service(self, *, actor_id: str, actor_role: str, user_email: Optional[str], user_phone: Optional[str], service_code: str, idempotency_key: Optional[str] = None) -> dict:
        user = self._get_user_by_email_or_phone(user_email, user_phone)
        if not user:
            raise ValueError("User not found")
        service = self._get_service_by_code(service_code)
        if not service:
            raise ValueError("Service not found")

        if idempotency_key:
            existing = db.fetch_one(
                """
                SELECT result FROM actions
                WHERE idempotency_key = :key AND action_name = 'deactivate_service' AND status = 'completed'
                """,
                {"key": idempotency_key},
            )
            if existing and existing.get("result"):
                return existing["result"]

        existing = db.fetch_one(
            """
            SELECT * FROM subscriptions
            WHERE user_id = :user_id AND service_id = :service_id
            """,
            {"user_id": user["id"], "service_id": service["id"]},
        )

        if not existing:
            raise ValueError("Subscription not found")

        db.execute(
            """
            UPDATE subscriptions
            SET status = 'cancelled', expires_at = NOW(), updated_at = NOW()
            WHERE id = :id
            """,
            {"id": existing["id"]},
        )

        action_id = secrets.token_hex(16)
        db.execute(
            """
            INSERT INTO actions (id, idempotency_key, session_id, user_id, action_name, status, requires_confirmation, params, result, created_at, completed_at)
            VALUES (:id, :idem, NULL, :user_id, 'deactivate_service', 'completed', 0, :params, :result, NOW(), NOW())
            """,
            {
                "id": action_id,
                "idem": idempotency_key or f"auto-{action_id}",
                "user_id": user["id"],
                "params": {"service_code": service_code},
                "result": {"status": "cancelled", "service_code": service_code},
            },
        )

        _write_audit(actor_id, actor_role, "deactivate_service", "subscription", existing["id"], {"service_code": service_code}, {"status": "cancelled"})
        logger.info("Deactivated %s for user %s", service_code, user["id"])
        return {
            "status": "cancelled",
            "service_code": service_code,
        }

    def list_subscriptions(self, *, user_email: Optional[str], user_phone: Optional[str]) -> list:
        user = self._get_user_by_email_or_phone(user_email, user_phone)
        if not user:
            raise ValueError("User not found")
        rows = db.fetch_all(
            """
            SELECT s.id, sv.code, sv.name, s.status, s.activated_at, s.expires_at
            FROM subscriptions s
            JOIN services sv ON sv.id = s.service_id
            WHERE s.user_id = :user_id
            ORDER BY s.updated_at DESC
            """,
            {"user_id": user["id"]},
        )
        return rows

    def list_tickets(self, *, user_email: Optional[str], user_phone: Optional[str]) -> list:
        user = self._get_user_by_email_or_phone(user_email, user_phone)
        if not user:
            raise ValueError("User not found")
        rows = db.fetch_all(
            """
            SELECT t.external_id, t.subject, t.priority, t.status, t.created_at, t.updated_at
            FROM tickets t
            WHERE t.user_id = :user_id
            ORDER BY t.updated_at DESC
            """,
            {"user_id": user["id"]},
        )
        return rows
