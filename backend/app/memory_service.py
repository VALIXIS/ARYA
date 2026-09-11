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
from .memory_validator import validate_memory, ALLOWED_CATEGORIES
from .memory_deduplicator import check_duplicate, SKIP, MERGE, SAVE


@dataclass
class MemorySnapshot:
    """Cached memory data detached from the database session."""

    id: int
    content: str
    category: str
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
        category=memory.category,
        created_at=memory.created_at,
    )


def save_memory(db: Session, memory: schemas.MemoryCreate) -> models.Memory | None:
    """
    Validate, deduplicate, then store a memory.

    Returns the Memory row on success, or None if the memory was rejected
    (failed validation) or was already covered by an existing memory.
    """
    content = memory.content.strip()
    category = memory.category or "Other"

    # --- 1. Validate -------------------------------------------------------
    if not validate_memory(content, category):
        return None

    # --- 2. Exact-match guard (fast path before dedup) ---------------------
    existing_exact = (
        db.query(models.Memory)
        .filter(func.lower(models.Memory.content) == content.lower())
        .first()
    )
    if existing_exact:
        return existing_exact

    # --- 3. Semantic deduplication ----------------------------------------
    all_snapshots = get_cached_memories(db)
    action, target = check_duplicate(content, all_snapshots)

    if action == SKIP:
        return None

    if action == MERGE:
        # Delete the older/less-detailed memory from DB
        db.query(models.Memory).filter(models.Memory.id == target.id).delete()
        db.commit()
        invalidate_memory_cache()
        # Refresh snapshots after deletion
        all_snapshots = get_cached_memories(db)

    # --- 4. Save the new memory --------------------------------------------
    db_memory = models.Memory(content=content, category=category)
    db.add(db_memory)
    db.commit()
    db.refresh(db_memory)
    invalidate_memory_cache()
    print(f"[MEMORY] Saved: {content!r} [{category}]")
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


# ---------------------------------------------------------------------------
# One-time cleanup migration
# ---------------------------------------------------------------------------

def run_cleanup_migration(db: Session) -> None:
    """
    Scan all existing memories, delete invalid ones, then deduplicate.
    Prints a summary on completion. Should be called once at startup
    (guarded by the memory_cleanup_v1_completed setting in main.py).
    """
    # Import here to avoid circular import at module level
    from . import memory_extractor as _me

    all_memories = get_all_memories(db)
    deleted_invalid = 0
    merged_count = 0

    # --- Pass 1: Reclassify & remove invalid memories ----------------------
    # Memories stored with category "Other" predate the category system.
    # Try to reclassify them. If reclassification fails or content is an
    # invalid fact (command / date / transient), delete them.
    to_delete_ids: set[int] = set()

    for mem in all_memories:
        cat = mem.category

        if cat not in ALLOWED_CATEGORIES:
            # Try to find a valid category via pattern matching
            extracted = _me.extract_memories(mem.content)
            if extracted:
                new_cat = extracted[0].get("category", "Other")
                if new_cat in ALLOWED_CATEGORIES:
                    # Reclassify in-place
                    db.query(models.Memory).filter(
                        models.Memory.id == mem.id
                    ).update({"category": new_cat})
                    print(f"[CLEANUP] Reclassified [{cat}] -> [{new_cat}]: {mem.content!r}")
                    mem.category = new_cat
                    continue

            # Could not reclassify AND content may still be valid — do a
            # content-only validity check with a neutral category guess.
            # If blocked patterns fire, delete it.
            from .memory_validator import _is_blocked
            if _is_blocked(mem.content):
                to_delete_ids.add(mem.id)
                deleted_invalid += 1
                print(f"[CLEANUP] Deleting blocked: {mem.content!r}")
            else:
                # It's a legit personal fact that just didn't match our patterns.
                # Assign "Preferences" as a safe fallback category.
                db.query(models.Memory).filter(
                    models.Memory.id == mem.id
                ).update({"category": "Preferences"})
                print(f"[CLEANUP] Fallback category Preferences: {mem.content!r}")
        else:
            # Category is already valid — just check for blocked content
            from .memory_validator import _is_blocked
            if _is_blocked(mem.content):
                to_delete_ids.add(mem.id)
                deleted_invalid += 1
                print(f"[CLEANUP] Deleting blocked: {mem.content!r}")

    if to_delete_ids:
        db.query(models.Memory).filter(
            models.Memory.id.in_(to_delete_ids)
        ).delete(synchronize_session=False)
        db.commit()
        invalidate_memory_cache()

    # --- Pass 2: Deduplicate remaining memories ----------------------------
    # Iterate oldest-first so we keep the most recent / most detailed version.
    remaining = (
        db.query(models.Memory)
        .order_by(models.Memory.created_at.asc())
        .all()
    )

    survived_snapshots: list[MemorySnapshot] = []
    merged_ids: set[int] = set()

    for mem in remaining:
        if mem.id in merged_ids:
            continue

        action, target = check_duplicate(mem.content, survived_snapshots)

        if action == SKIP:
            # mem is redundant compared to something already in survived
            merged_ids.add(mem.id)
            db.query(models.Memory).filter(models.Memory.id == mem.id).delete()
            merged_count += 1

        elif action == MERGE:
            # mem should replace something already in survived
            # Remove the weaker survived entry
            survived_snapshots = [s for s in survived_snapshots if s.id != target.id]
            db.query(models.Memory).filter(models.Memory.id == target.id).delete()
            merged_count += 1
            survived_snapshots.append(_snapshot(mem))

        else:  # SAVE
            survived_snapshots.append(_snapshot(mem))

    db.commit()
    invalidate_memory_cache()

    remaining_count = db.query(models.Memory).count()

    print("")
    print("[MEMORY CLEANUP]")
    print(f"  Deleted invalid:   {deleted_invalid}")
    print(f"  Merged duplicates: {merged_count}")
    print(f"  Remaining memories: {remaining_count}")
    print("")


def delete_memory_by_id(db: Session, memory_id: int) -> bool:
    """Delete a memory by its primary key ID."""
    mem = db.query(models.Memory).filter(models.Memory.id == memory_id).first()
    if mem:
        db.delete(mem)
        db.commit()
        invalidate_memory_cache()
        return True
    return False

