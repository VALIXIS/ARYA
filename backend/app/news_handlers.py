"""
news_handlers.py
----------------
Backend integration layer for ARYA news commands and API routes.
"""

from . import news_commands, news_service, performance_service

NEWS_DISABLED_REPLY = "News is currently disabled."


def _disabled_news_response() -> dict:
    """Return an empty news payload when news is disabled."""
    return {
        "ai_news": [],
        "technology_news": [],
        "cached": False,
        "last_updated": None,
    }


def _log_news_fetch(start_time: float) -> None:
    """Record news fetch timing."""
    news_ms = performance_service.elapsed_ms(start_time)
    performance_service.log_timing("news_fetch", news_ms)
    performance_service.log_perf("News fetch", news_ms)


def get_news_endpoint_response() -> dict:
    """Return structured news data for GET /news."""
    if not news_service.is_news_enabled():
        return _disabled_news_response()

    start_time = performance_service.start_timer()
    data = news_service.get_news()
    _log_news_fetch(start_time)
    return data


def handle_chat_command(message: str) -> str | None:
    """
    Handle a news chat command.

    Returns a reply string when the message matches a news command,
    otherwise returns None.
    """
    is_daily_briefing = news_commands.detect_daily_news_briefing(message)
    is_ai_news = news_commands.detect_ai_news_query(message)
    is_whats_happening = news_commands.detect_whats_happening(message)

    if not (is_daily_briefing or is_ai_news or is_whats_happening):
        return None

    if not news_service.is_news_enabled():
        return NEWS_DISABLED_REPLY

    start_time = performance_service.start_timer()

    if is_daily_briefing:
        reply = news_service.format_full_briefing()
    elif is_ai_news:
        reply = news_service.format_ai_news()
    else:
        reply = news_service.format_whats_happening()

    _log_news_fetch(start_time)
    return reply
