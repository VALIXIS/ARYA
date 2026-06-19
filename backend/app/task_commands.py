"""
task_commands.py
----------------
Simple rule-based task command detection.
No AI calls, embeddings, or NLP libraries are used here.
"""


def _clean_text(text: str) -> str:
    """Clean extracted command text."""
    return text.strip(" \t\r\n.,!?;:")


def detect_task_create(message: str) -> str | None:
    """Return a task title if the user wants to add a task."""
    text = message.strip()
    lower_text = text.lower()

    prefixes = (
        "add task ",
        "create task ",
        "new task ",
        "task ",
        "todo ",
        "remind me to ",
    )

    for prefix in prefixes:
        if lower_text.startswith(prefix):
            return _clean_text(text[len(prefix) :])

    return None


def detect_task_query(message: str) -> bool:
    """Return True if the user wants to see tasks."""
    text = message.strip().lower().strip(" \t\r\n.,!?;:")
    words = {
        word.strip(" \t\r\n.,!?;:\"'()[]{}")
        for word in text.split()
        if word.strip(" \t\r\n.,!?;:\"'()[]{}")
    }

    if "task" not in words and "tasks" not in words and "todo" not in words:
        return False

    return "show" in words or "list" in words or "what" in words


def detect_task_complete(message: str) -> str | None:
    """Return a task search query if the user wants to complete a task."""
    text = message.strip()
    lower_text = text.lower()

    prefixes = (
        "complete task ",
        "finish task ",
        "mark task complete ",
        "mark task done ",
    )

    for prefix in prefixes:
        if lower_text.startswith(prefix):
            return _clean_text(text[len(prefix) :])

    return None
