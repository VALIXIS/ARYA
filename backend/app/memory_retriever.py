"""
memory_retriever.py
-------------------
Small retrieval layer for finding memories relevant to a chat message.
It reuses the existing memory search logic so ARYA has one simple path
for keyword-based memory lookup.
"""

from sqlalchemy.orm import Session

from . import memory_service


STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "do",
    "for",
    "how",
    "i",
    "is",
    "it",
    "me",
    "my",
    "of",
    "the",
    "to",
    "what",
    "when",
    "where",
    "who",
    "why",
    "you",
}


def _keywords(message: str) -> list[str]:
    """Extract simple keyword search terms from a chat message."""
    words = []
    for raw_word in message.lower().split():
        word = raw_word.strip(".,!?;:\"'()[]{}")
        if len(word) > 2 and word not in STOP_WORDS:
            words.append(word)
    return words


def retrieve_relevant_memories(db: Session, message: str, limit: int = 5) -> list[str]:
    """Return memory contents that match the user's message."""
    keywords = _keywords(message)
    if not keywords:
        return []

    relevant_memories = []
    seen_ids = set()

    for keyword in keywords:
        for memory in memory_service.search_memories(db, keyword):
            if memory.id not in seen_ids:
                seen_ids.add(memory.id)
                relevant_memories.append(memory.content)

            if len(relevant_memories) >= limit:
                return relevant_memories

    return relevant_memories
