"""
browser_tools.py
----------------
Browser-related tools: open website, search Google, search/play YouTube.

Registers 4 tools on import:
    open_website, google_search, youtube_search, youtube_play
"""

import webbrowser
import urllib.parse

from .tool_registry import registry
from .tool_schemas import ToolSchema, ToolCategory, ToolParam, ParamType, ToolResult

import os
import sys
import urllib.request
import urllib.parse
import re

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _open_url(url: str, tool_name: str) -> ToolResult:
    print(f"[BROWSER] Opening:\n{url}")
    try:
        if sys.platform == "win32":
            os.startfile(url)
            ok = True
        else:
            ok = webbrowser.open(url)
            
        print(f"[BROWSER] Success: {ok}")
        if ok:
            return ToolResult(success=True, message=f"Opened {url}.", detail=f"Result: {ok}")
        return ToolResult(success=False, message=f"Browser failed to open {url}.", error="Browser execution failed")
    except Exception as exc:
        err = f"{type(exc).__name__}: {exc}"
        print(f"[BROWSER] Success: False ({err})")
        return ToolResult(success=False, message=f"Failed to open browser: {exc}", error=err)

def _scrape_first_youtube_video(query: str) -> str | None:
    """Scrape the first video ID from YouTube search results."""
    search_url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
    try:
        req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8')
        match = re.search(r'"videoId":"(.*?)"', html)
        if match:
            return f"https://www.youtube.com/watch?v={match.group(1)}"
    except Exception as exc:
        print(f"[BROWSER] Error scraping YouTube: {exc}")
    return None

# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def _open_website(params: dict) -> ToolResult:
    url: str = params["url"].strip()
    if not url.startswith(("http://", "https://", "ms-settings:")):
        url = "https://" + url
    return _open_url(url, "open_website")


def _google_search(params: dict) -> ToolResult:
    query: str = params["query"].strip()
    url = "https://google.com/search?q=" + urllib.parse.quote_plus(query)
    return _open_url(url, "google_search")


def _youtube_search(params: dict) -> ToolResult:
    query: str = params["query"].strip()
    url = "https://youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
    return _open_url(url, "youtube_search")


def _youtube_play(params: dict) -> ToolResult:
    query: str = params["query"].strip()
    video_url = _scrape_first_youtube_video(query)
    
    if video_url:
        print(f"[MEDIA] Playing: {video_url}")
        res = _open_url(video_url, "youtube_play")
        if res.success:
            res.message = f"Playing '{query}' on YouTube."
        return res
        
    # Fallback to search
    fallback = "https://youtube.com/search?q=" + urllib.parse.quote_plus(query)
    return _open_url(fallback, "youtube_play")

# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

registry.register(
    schema=ToolSchema(
        name="open_website",
        description="Open any URL or website in the default browser.",
        category=ToolCategory.BROWSER,
        params=[ToolParam("url", ParamType.URL, "Full URL or domain, e.g. 'youtube.com'")],
        examples=["open youtube.com", "open google.com", "go to github.com"],
    ),
    handler=_open_website,
)

registry.register(
    schema=ToolSchema(
        name="google_search",
        description="Search Google for a query and open the results in the browser.",
        category=ToolCategory.BROWSER,
        params=[ToolParam("query", ParamType.STRING, "The search query")],
        examples=["search python tutorials", "google AI news"],
    ),
    handler=_google_search,
)

registry.register(
    schema=ToolSchema(
        name="youtube_search",
        description="Search YouTube for videos matching a query.",
        category=ToolCategory.BROWSER,
        params=[ToolParam("query", ParamType.STRING, "The search query")],
        examples=["search youtube telugu songs", "find python tutorials on youtube"],
    ),
    handler=_youtube_search,
)

registry.register(
    schema=ToolSchema(
        name="youtube_play",
        description="Play a song, video, or topic on YouTube.",
        category=ToolCategory.BROWSER,
        params=[ToolParam("query", ParamType.STRING, "Song name, video title, or topic to play")],
        examples=["play telugu songs", "play lo-fi music", "play SPB songs"],
    ),
    handler=_youtube_play,
)
