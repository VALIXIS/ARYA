"""
profile_commands.py
-------------------
Detects simple user profile requests.
No AI calls, embeddings, or NLP libraries are used here.
"""


def _words(message: str) -> set[str]:
    """Return normalized words for lightweight keyword matching."""
    return {
        word.strip(" \t\r\n.,!?;:\"'()[]{}").lower()
        for word in message.split()
        if word.strip(" \t\r\n.,!?;:\"'()[]{}")
    }


def detect_profile_query(message: str) -> bool:
    """Return True if the user is asking for their profile."""
    words = _words(message)

    says_you = "you" in words or "u" in words
    says_about = "about" in words or "abt" in words
    mentions_me = "me" in words or "myself" in words

    if "show" in words and "profile" in words:
        return True

    if "who" in words and "am" in words and "i" in words:
        return True

    if "tell" in words and says_about and "myself" in words:
        return True

    if "know" in words and says_you and says_about and mentions_me:
        return True

    return False
