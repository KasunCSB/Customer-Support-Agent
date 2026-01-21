"""
Lightweight database helper using SQLAlchemy.

Provides simple helpers for fetching and executing statements with the
configured MySQL connection string.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, Result

from src.config import settings
from src.logger import get_logger

logger = get_logger(__name__)

_engine: Optional[Engine] = None


def get_engine() -> Engine:
    """Get a singleton SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.database.url,
            pool_pre_ping=True,
        )
        logger.info("Database engine initialized")
    return _engine


class Database:
    """Thin wrapper around SQLAlchemy engine for common operations."""

    def __init__(self, engine: Optional[Engine] = None) -> None:
        self.engine = engine or get_engine()

    def execute(self, sql: str, params: Optional[Mapping[str, Any]] = None) -> Result:
        with self.engine.begin() as conn:
            return conn.execute(text(sql), params or {})

    def fetch_one(self, sql: str, params: Optional[Mapping[str, Any]] = None) -> Optional[Mapping[str, Any]]:
        result = self.execute(sql, params)
        row = result.mappings().first()
        return dict(row) if row else None

    def fetch_all(self, sql: str, params: Optional[Mapping[str, Any]] = None) -> Sequence[Mapping[str, Any]]:
        result = self.execute(sql, params)
        return [dict(r) for r in result.mappings().all()]


db = Database()
