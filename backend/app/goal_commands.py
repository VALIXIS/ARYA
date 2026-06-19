"""
goal_commands.py
----------------
Simple rule-based goal command detection.
No AI calls, embeddings, or NLP libraries are used here.
"""


def _clean_text(text: str) -> str:
    """Clean extracted command text."""
    return text.strip(" \t\r\n.,!?;:")


def detect_goal_create(message: str) -> str | None:
    """Return a goal title if the user wants to create a goal."""
    text = message.strip()
    lower_text = text.lower()

    if lower_text.startswith("my goal is "):
        return _clean_text(text[len("my goal is ") :])

    if lower_text.startswith("i want to "):
        return _clean_text(text[len("i want to ") :])

    if lower_text.startswith("add goal "):
        return _clean_text(text[len("add goal ") :])

    return None


def detect_goal_query(message: str) -> bool:
    """Return True if the user wants to see goals."""
    text = message.strip().lower().strip(" \t\r\n.,!?;:")
    words = {
        word.strip(" \t\r\n.,!?;:\"'()[]{}")
        for word in text.split()
        if word.strip(" \t\r\n.,!?;:\"'()[]{}")
    }

    if "goal" not in words and "goals" not in words:
        return False

    return "show" in words or "what" in words or "list" in words


def detect_goal_complete(message: str) -> str | None:
    """Return a goal search query if the user wants to complete a goal."""
    text = message.strip()
    lower_text = text.lower()

    if lower_text.startswith("complete goal "):
        return _clean_text(text[len("complete goal ") :])

    return None
