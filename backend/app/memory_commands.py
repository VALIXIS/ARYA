"""
memory_commands.py
------------------
Simple command detection for managing memories through chat.
This intentionally avoids NLP frameworks and only handles clear,
human-readable memory commands.
"""


def _clean_text(text: str) -> str:
    """Normalize command text after removing the command phrase."""
    return text.strip(" \t\r\n.,!?;:")


def detect_remember_command(message: str) -> str | None:
    """
    Return memory content if the user wants ARYA to remember something.

    Supported examples:
        Remember that I like tea
        Remember my favorite color is blue
    """
    text = message.strip()
    lower_text = text.lower()

    if lower_text.startswith("remember that "):
        return _clean_text(text[len("remember that ") :])

    if lower_text.startswith("remember "):
        return _clean_text(text[len("remember ") :])

    return None


def detect_forget_command(message: str) -> str | None:
    """
    Return search text if the user wants ARYA to forget matching memories.

    Supported example:
        Forget my favorite color
    """
    text = message.strip()
    lower_text = text.lower()

    if lower_text.startswith("forget "):
        return _clean_text(text[len("forget ") :])

    return None


def detect_memory_query(message: str) -> bool:
    """
    Return True if the user is asking to see stored memories.

    Supported examples:
        What do you remember about me?
        What do u remember about me?
        What do you know about me?
        Show my memories
        List my memories
        Tell me what you remember about me
    """
    text = message.strip().lower().strip(" \t\r\n.,!?;:")
    words = set(text.split())

    if ("show" in words or "list" in words) and (
        "memories" in words or "memory" in words
    ):
        return True

    mentions_user = "me" in words or "my" in words
    says_you = "you" in words or "u" in words
    asks_about_memory = "remember" in words or "know" in words

    return mentions_user and says_you and asks_about_memory
