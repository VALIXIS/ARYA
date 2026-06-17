"""
memory_service.py
------------------
Business logic for saving and retrieving memories. Keeping this logic
separate from main.py means the API routes stay thin, and the logic
itself is easy to test or reuse later.
"""

from sqlalchemy.orm import Session

from . import models, schemas


def save_memory(db: Session, memory: schemas.MemoryCreate) -> models.Memory:
    """Create and store a new memory."""
    db_memory = models.Memory(content=memory.content)
    db.add(db_memory)
    db.commit()
    db.refresh(db_memory)
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
