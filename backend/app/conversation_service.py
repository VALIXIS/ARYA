"""
conversation_service.py
-----------------------
Stores and retrieves recent conversation messages for ARYA.
The history is intentionally small and simple: SQLite rows ordered by time.
"""

from dataclasses import dataclass
from datetime import datetime

from . import models
from .database import SessionLocal


@dataclass
class ConversationSnapshot:
    """Cached conversation data detached from the database session."""

    id: int
    role: str
    content: str
    created_at: datetime


_recent_messages_cache: list[ConversationSnapshot] | None = None


def invalidate_conversation_cache() -> None:
    """Clear cached conversation history after writes."""
    global _recent_messages_cache
    _recent_messages_cache = None


def _snapshot(message: models.Conversation) -> ConversationSnapshot:
    """Convert a SQLAlchemy conversation row into cached data."""
    return ConversationSnapshot(
        id=message.id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
    )


def add_message(role: str, content: str) -> models.Conversation:
    """Save one conversation message."""
    db = SessionLocal()
    try:
        message = models.Conversation(role=role, content=content)
        db.add(message)
        db.commit()
        db.refresh(message)
        invalidate_conversation_cache()
        return message
    finally:
        db.close()


def add_messages(messages: list[tuple[str, str]]) -> None:
    """Save multiple conversation messages in one database transaction."""
    db = SessionLocal()
    try:
        for role, content in messages:
            db.add(models.Conversation(role=role, content=content))
        db.commit()
        invalidate_conversation_cache()
    finally:
        db.close()


def get_recent_messages(limit: int = 10) -> list[models.Conversation]:
    """Return the most recent conversation messages in chronological order."""
    db = SessionLocal()
    try:
        messages = (
            db.query(models.Conversation)
            .order_by(models.Conversation.created_at.desc(), models.Conversation.id.desc())
            .limit(limit)
            .all()
        )
        return list(reversed(messages))
    finally:
        db.close()


def get_cached_recent_messages(limit: int = 10) -> list[ConversationSnapshot]:
    """Return cached recent conversation messages."""
    global _recent_messages_cache
    if _recent_messages_cache is None:
        _recent_messages_cache = [
            _snapshot(message) for message in get_recent_messages(limit=limit)
        ]
    return _recent_messages_cache[-limit:]
