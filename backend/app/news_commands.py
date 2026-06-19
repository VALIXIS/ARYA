"""
news_commands.py
----------------
Simple rule-based news command detection.
No AI calls, embeddings, or NLP libraries are used here.
"""


def _normalize(message: str) -> str:
    """Normalize user text for lightweight phrase matching."""
    return message.strip().lower().strip(" \t\r\n.,!?;:")


def detect_daily_news_briefing(message: str) -> bool:
    """
    Return True for a full daily news briefing request.

    Supported examples:
        Daily news briefing
        Today's news briefing
    """
    text = _normalize(message)
    phrases = (
        "daily news briefing",
        "today's news briefing",
        "todays news briefing",
    )
    return any(phrase in text for phrase in phrases)


def detect_ai_news_query(message: str) -> bool:
    """
    Return True when the user asks for today's AI news.

    Supported examples:
        Give me today's AI news
        Today's AI news
    """
    text = _normalize(message)
    phrases = (
        "give me today's ai news",
        "give me todays ai news",
        "today's ai news",
        "todays ai news",
    )
    return any(phrase in text for phrase in phrases)


def detect_whats_happening(message: str) -> bool:
    """
    Return True when the user asks what's happening today.

    Supported examples:
        What's happening today?
        What is happening today?
    """
    text = _normalize(message)
    phrases = (
        "what's happening today",
        "whats happening today",
        "what is happening today",
    )
    return any(phrase in text for phrase in phrases)
