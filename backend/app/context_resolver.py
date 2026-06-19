"""
context_resolver.py
-------------------
Lightweight follow-up question resolver for vague pronouns.
No AI calls, embeddings, or NLP libraries are used here.
"""

from typing import Any


VAGUE_PRONOUNS = {"it", "that", "this", "they", "them"}


def _clean_text(text: str) -> str:
    """Normalize text for simple matching."""
    return text.strip(" \t\r\n.,!?;:")


def _words(text: str) -> set[str]:
    """Return lowercase words stripped of common punctuation."""
    return {
        word.strip(" \t\r\n.,!?;:\"'()[]{}").lower()
        for word in text.split()
        if word.strip(" \t\r\n.,!?;:\"'()[]{}")
    }


def _last_user_message(recent_messages: list[Any]) -> str | None:
    """Find the latest user message in recent conversation history."""
    for message in reversed(recent_messages):
        if getattr(message, "role", None) == "user":
            return getattr(message, "content", None)
    return None


def _extract_subject(message: str) -> str | None:
    """Extract a simple subject from a personal fact sentence."""
    text = _clean_text(message)
    lower_text = text.lower()

    for separator in (" is ", " are ", " was ", " were "):
        if separator in lower_text:
            index = lower_text.index(separator)
            subject = _clean_text(text[:index])
            if subject:
                return subject[0].lower() + subject[1:]

    return None


def resolve_message(current_message, recent_messages):
    """Rewrite vague follow-up questions using recent conversation context."""
    current_text = _clean_text(current_message)
    current_words = _words(current_text)

    if not current_words.intersection(VAGUE_PRONOUNS):
        return current_message

    last_user_message = _last_user_message(recent_messages)
    if not last_user_message:
        return current_message

    subject = _extract_subject(last_user_message)
    if not subject:
        return current_message

    lower_current = current_text.lower()
    if lower_current.startswith("what is ") or lower_current.startswith("what's "):
        return f"What is {subject}?"

    if lower_current.startswith("what are "):
        return f"What are {subject}?"

    return current_message
