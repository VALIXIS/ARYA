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
import json
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
    """
    Scrape the first real organic video from YouTube search results.
    Bypasses sponsored ads, promotional banners, and carousel recommendations
    by parsing videoRenderer entries and matching relevance.
    """
    search_url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
    print(f"[MEDIA] YouTube search URL: {search_url}")
    try:
        req = urllib.request.Request(
            search_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        html = urllib.request.urlopen(req, timeout=8).read().decode("utf-8", errors="replace")

        # 1. Primary Method: Extract from ytInitialData JSON structure
        m_json = re.search(r'var ytInitialData = ({.*?});</script>', html)
        if not m_json:
            m_json = re.search(r'ytInitialData\s*=\s*({.+?});', html)

        if m_json:
            try:
                data = json.loads(m_json.group(1))
                candidates: list[tuple[str, str]] = []

                def _extract_renderers(obj):
                    if isinstance(obj, dict):
                        if "videoRenderer" in obj:
                            vr = obj["videoRenderer"]
                            vid = vr.get("videoId")
                            title_runs = vr.get("title", {}).get("runs", [])
                            title = title_runs[0].get("text", "") if title_runs else ""
                            if vid and len(vid) == 11:
                                candidates.append((vid, title))
                        for v in obj.values():
                            _extract_renderers(v)
                    elif isinstance(obj, list):
                        for item in obj:
                            _extract_renderers(item)

                _extract_renderers(data)

                if candidates:
                    # Filter against query keywords (e.g. "shreya", "ghoshal")
                    query_words = [
                        w.lower() for w in re.findall(r"\b\w{3,}\b", query)
                        if w.lower() not in {"song", "songs", "play", "video", "youtube", "music", "audio"}
                    ]
                    chosen_vid = candidates[0][0]
                    chosen_title = candidates[0][1]

                    if query_words:
                        for vid, title in candidates[:12]:
                            t_lower = title.lower()
                            if any(qw in t_lower for qw in query_words):
                                chosen_vid = vid
                                chosen_title = title
                                break

                    watch_url = f"https://www.youtube.com/watch?v={chosen_vid}"
                    print(f"[MEDIA] Selected organic video: '{chosen_title}' -> {watch_url}")
                    return watch_url
            except Exception as j_exc:
                print(f"[MEDIA] ytInitialData parse failed: {j_exc}")

        # 2. Targeted regex fallback for videoRenderer (ignores promoted ad banners)
        vr_matches = re.findall(r'"videoRenderer":\s*\{\s*"videoId":\s*"([a-zA-Z0-9_-]{11})"', html)
        if vr_matches:
            watch_url = f"https://www.youtube.com/watch?v={vr_matches[0]}"
            print(f"[MEDIA] Selected via videoRenderer regex: {watch_url}")
            return watch_url

        # 3. Fallback: generic videoId
        for vid in re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', html):
            watch_url = f"https://www.youtube.com/watch?v={vid}"
            print(f"[MEDIA] Selected via generic regex: {watch_url}")
            return watch_url

        print("[MEDIA] No videoId found in YouTube HTML")
    except Exception as exc:
        print(f"[MEDIA] YouTube scrape error: {exc}")
    return None


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def _open_website(params: dict) -> ToolResult:
    raw_url: str = params["url"].strip()
    # Web app shortcuts mapping
    aliases = {
        "gmail": "https://mail.google.com",
        "google mail": "https://mail.google.com",
        "mail": "https://mail.google.com",
        "youtube": "https://youtube.com",
        "yt": "https://youtube.com",
        "whatsapp": "https://web.whatsapp.com",
        "github": "https://github.com",
        "chatgpt": "https://chatgpt.com",
        "maps": "https://maps.google.com",
        "google maps": "https://maps.google.com",
        "netflix": "https://netflix.com",
        "spotify": "https://open.spotify.com",
        "twitter": "https://x.com",
        "x": "https://x.com",
        "reddit": "https://reddit.com",
        "drive": "https://drive.google.com",
        "google drive": "https://drive.google.com",
        "docs": "https://docs.google.com",
        "google docs": "https://docs.google.com",
    }
    url = aliases.get(raw_url.lower(), raw_url)
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
        # Append autoplay=1 so video starts playing immediately
        sep = "&" if "?" in video_url else "?"
        autoplay_url = f"{video_url}{sep}autoplay=1"
        print(f"[MEDIA] Playing with autoplay: {autoplay_url}")
        res = _open_url(autoplay_url, "youtube_play")
        if res.success:
            res.message = f"Playing '{query}' on YouTube."
        return res
        
    # Fallback to search
    fallback = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
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
