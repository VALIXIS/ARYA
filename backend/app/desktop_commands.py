"""
desktop_commands.py
-------------------
Simple rule-based desktop action command detection.
No AI calls, embeddings, or NLP libraries are used here.
"""


def detect_desktop_action(message: str) -> str | None:
    """Return a supported desktop action name if one is requested."""
    text = message.strip().lower()

    if "open" not in text and "launch" not in text:
        return None

    if "chrome" in text:
        return "chrome"

    if "vs code" in text or "vscode" in text or "visual studio code" in text:
        return "vscode"

    if "downloads" in text or "download folder" in text:
        return "downloads"

    if "file explorer" in text or "explorer" in text:
        return "file_explorer"

    return None
