"""
news_service.py
---------------
Fetch AI and technology news for ARYA.

Uses NewsAPI when NEWS_API_KEY is set, otherwise falls back to RSS feeds.
Results are cached in memory for 30 minutes.
"""

import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

ENABLE_NEWS = os.getenv("ENABLE_NEWS", "true").lower() in {"true", "1", "yes"}
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "").strip()

CACHE_TTL_SECONDS = 30 * 60
MAX_HEADLINES = 5

AI_NEWS_RSS_URL = (
    "https://news.google.com/rss/search?q=artificial+intelligence"
    "&hl=en-US&gl=US&ceid=US:en"
)
TECHNOLOGY_NEWS_RSS_URL = (
    "https://news.google.com/rss/search?q=technology"
    "&hl=en-US&gl=US&ceid=US:en"
)

REQUEST_HEADERS = {"User-Agent": "ARYA/1.0"}
REQUEST_TIMEOUT = 10

_cache: dict = {
    "fetched_at": None,
    "ai_news": [],
    "technology_news": [],
}


def is_news_enabled() -> bool:
    """Return True when news fetching is enabled."""
    return ENABLE_NEWS


def _is_cache_valid() -> bool:
    """Return True when cached news is still fresh."""
    fetched_at = _cache["fetched_at"]
    if fetched_at is None:
        return False
    return (time.time() - fetched_at) < CACHE_TTL_SECONDS


def _iso_timestamp(timestamp: float | None) -> str | None:
    """Convert a Unix timestamp to an ISO-8601 UTC string."""
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _build_response(*, served_from_cache: bool) -> dict:
    """Build the structured news response."""
    return {
        "ai_news": list(_cache["ai_news"]),
        "technology_news": list(_cache["technology_news"]),
        "cached": served_from_cache,
        "last_updated": _iso_timestamp(_cache["fetched_at"]),
    }


def _normalize_headline(title: str, link: str = "", source: str = "") -> dict:
    """Normalize one headline into the ARYA news shape."""
    return {
        "title": title.strip(),
        "link": link.strip(),
        "source": source.strip(),
    }


def _dedupe_headlines(items: list[dict]) -> list[dict]:
    """Remove duplicate headlines while preserving order."""
    seen: set[str] = set()
    unique_items: list[dict] = []

    for item in items:
        title = item.get("title", "").strip()
        if not title:
            continue

        key = title.lower()
        if key in seen:
            continue

        seen.add(key)
        unique_items.append(item)

    return unique_items[:MAX_HEADLINES]


def _fetch_newsapi_ai_news() -> list[dict]:
    """Fetch AI headlines from NewsAPI."""
    response = requests.get(
        "https://newsapi.org/v2/everything",
        params={
            "q": "artificial intelligence",
            "sortBy": "publishedAt",
            "pageSize": MAX_HEADLINES,
            "language": "en",
            "apiKey": NEWS_API_KEY,
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return _parse_newsapi_articles(response.json().get("articles", []))


def _fetch_newsapi_technology_news() -> list[dict]:
    """Fetch technology headlines from NewsAPI."""
    response = requests.get(
        "https://newsapi.org/v2/top-headlines",
        params={
            "category": "technology",
            "country": "us",
            "pageSize": MAX_HEADLINES,
            "apiKey": NEWS_API_KEY,
        },
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return _parse_newsapi_articles(response.json().get("articles", []))


def _parse_newsapi_articles(articles: list[dict]) -> list[dict]:
    """Convert NewsAPI articles into ARYA headline objects."""
    headlines: list[dict] = []

    for article in articles:
        title = (article.get("title") or "").strip()
        if not title or title == "[Removed]":
            continue

        source = article.get("source") or {}
        source_name = source.get("name", "") if isinstance(source, dict) else str(source)
        headlines.append(
            _normalize_headline(
                title=title,
                link=article.get("url") or "",
                source=source_name,
            )
        )

    return _dedupe_headlines(headlines)


def _fetch_rss_news(url: str) -> list[dict]:
    """Fetch headlines from an RSS feed."""
    response = requests.get(
        url,
        headers=REQUEST_HEADERS,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    root = ET.fromstring(response.content)
    headlines: list[dict] = []

    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        if not title:
            continue

        headlines.append(
            _normalize_headline(
                title=title,
                link=(item.findtext("link") or "").strip(),
                source=(item.findtext("source") or "").strip(),
            )
        )

    return _dedupe_headlines(headlines)


def _fetch_fresh_news() -> None:
    """Fetch fresh headlines using NewsAPI or RSS fallback."""
    ai_news: list[dict] = []
    technology_news: list[dict] = []

    if NEWS_API_KEY:
        try:
            ai_news = _fetch_newsapi_ai_news()
            technology_news = _fetch_newsapi_technology_news()
        except Exception:
            ai_news = []
            technology_news = []

    if not ai_news:
        ai_news = _fetch_rss_news(AI_NEWS_RSS_URL)

    if not technology_news:
        technology_news = _fetch_rss_news(TECHNOLOGY_NEWS_RSS_URL)

    _cache["ai_news"] = _dedupe_headlines(ai_news)
    _cache["technology_news"] = _dedupe_headlines(technology_news)
    _cache["fetched_at"] = time.time()


def get_news(*, force_refresh: bool = False) -> dict:
    """
    Return structured news data.

    Response shape:
        {
            "ai_news": [...],
            "technology_news": [...],
            "cached": true,
            "last_updated": "..."
        }
    """
    if not ENABLE_NEWS:
        return {
            "ai_news": [],
            "technology_news": [],
            "cached": False,
            "last_updated": None,
        }

    if not force_refresh and _is_cache_valid():
        return _build_response(served_from_cache=True)

    try:
        _fetch_fresh_news()
        return _build_response(served_from_cache=False)
    except Exception:
        if _cache["fetched_at"] is not None:
            return _build_response(served_from_cache=True)

        return {
            "ai_news": [],
            "technology_news": [],
            "cached": False,
            "last_updated": None,
        }


def _format_section(title: str, headlines: list[dict], limit: int = MAX_HEADLINES) -> str:
    """Format one news section for chat responses."""
    if not headlines:
        return f"{title}\n(unable to fetch news)"

    lines = "\n".join(f"- {item['title']}" for item in headlines[:limit])
    return f"{title}\n{lines}"


def format_ai_news(limit: int = MAX_HEADLINES) -> str:
    """Format AI news headlines."""
    data = get_news()
    return _format_section("AI News", data["ai_news"], limit)


def format_technology_news(limit: int = MAX_HEADLINES) -> str:
    """Format technology news headlines."""
    data = get_news()
    return _format_section("Technology News", data["technology_news"], limit)


def format_full_briefing(limit: int = MAX_HEADLINES) -> str:
    """Format the full news briefing."""
    data = get_news()
    sections = [
        _format_section("AI News", data["ai_news"], limit),
        _format_section("Technology News", data["technology_news"], limit),
    ]
    return "\n\n".join(sections)


def format_whats_happening(limit: int = 3) -> str:
    """Format a compact summary of today's headlines."""
    data = get_news()
    sections = [
        "Here's what's happening today:",
        _format_section("AI News", data["ai_news"], limit),
        _format_section("Technology News", data["technology_news"], limit),
    ]
    return "\n\n".join(sections)
