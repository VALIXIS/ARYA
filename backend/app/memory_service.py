"""
memory_service.py
------------------
Business logic for saving and retrieving memories. Keeping this logic
separate from main.py means the API routes stay thin, and the logic
itself is easy to test or reuse later.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from dataclasses import dataclass
from datetime import datetime

from . import models, schemas


@dataclass
class MemorySnapshot:
    """Cached memory data detached from the database session."""

    id: int
    content: str
    created_at: datetime


_memory_cache: list[MemorySnapshot] | None = None


def invalidate_memory_cache() -> None:
    """Clear cached memories after writes."""
    global _memory_cache
    _memory_cache = None


def _snapshot(memory: models.Memory) -> MemorySnapshot:
    """Convert a SQLAlchemy memory row into cached data."""
    return MemorySnapshot(
        id=memory.id,
        content=memory.content,
        created_at=memory.created_at,
    )


def save_memory(db: Session, memory: schemas.MemoryCreate) -> models.Memory:
    """Create and store a new memory if it does not already exist."""
    content = memory.content.strip()
    existing_memory = (
        db.query(models.Memory)
        .filter(func.lower(models.Memory.content) == content.lower())
        .first()
    )
    if existing_memory:
        return existing_memory

    db_memory = models.Memory(content=content)
    db.add(db_memory)
    db.commit()
    db.refresh(db_memory)
    invalidate_memory_cache()
    return db_memory


def get_all_memories(db: Session):
    """Return every memory, newest first."""
    return db.query(models.Memory).order_by(models.Memory.created_at.desc()).all()


def search_memories(db: Session, query: str):
    """Return memories whose content contains the given text (case-insensitive)."""
    return (
        db.query(models.Memory)
        .filter(models.Memory.content.ilike(f"%{query}%"))
        .order_by(models.Memory.created_at.desc())
        .all()
    )


def delete_memory(db: Session, query: str) -> int:
    """Delete memories whose content contains the given text and return the count."""
    memories = search_memories(db, query)

    for memory in memories:
        db.delete(memory)

    db.commit()
    invalidate_memory_cache()
    return len(memories)


def get_cached_memories(db: Session) -> list[MemorySnapshot]:
    """Return cached memories, loading them from the database once when needed."""
    global _memory_cache
    if _memory_cache is None:
        _memory_cache = [_snapshot(memory) for memory in get_all_memories(db)]
    return _memory_cache
