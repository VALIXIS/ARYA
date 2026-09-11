"""
weather_tools.py
------------------
Live Information & Weather tools for Project ARYA.
Fetches real-time weather forecasts worldwide using Open-Meteo (zero API key)
and instant web intelligence for general knowledge questions.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

from .tool_registry import registry
from .tool_schemas import ToolCategory, ToolParam, ToolResult, ToolSchema, ParamType

WEATHER_CODES = {
    0: "clear sunny skies",
    1: "mostly clear skies",
    2: "partly cloudy skies",
    3: "overcast clouds",
    45: "foggy conditions",
    48: "depositing rime fog",
    51: "light drizzle",
    53: "moderate drizzle",
    55: "dense drizzle",
    61: "slight rain showers",
    63: "moderate rain",
    65: "heavy rain showers",
    71: "slight snow showers",
    73: "moderate snowfall",
    75: "heavy snowfall",
    80: "isolated rain showers",
    81: "scattered rain showers",
    82: "violent rain storms",
    95: "thunderstorms",
    96: "thunderstorms with slight hail",
    99: "severe thunderstorms with heavy hail",
}


def _get_weather(params: dict[str, Any]) -> ToolResult:
    """Fetch live real-time weather or forecast for any city (default: Guntur)."""
    raw_loc = params.get("location") or "Guntur"
    loc_clean = str(raw_loc).strip().title()
    period = str(params.get("period") or "today").lower().strip()

    try:
        # 1. Geocoding
        geo_url = (
            f"https://geocoding-api.open-meteo.com/v1/search?name="
            f"{urllib.parse.quote_plus(loc_clean)}&count=1&language=en&format=json"
        )
        req = urllib.request.Request(geo_url, headers={"User-Agent": "ARYA-AI/2.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            geo_data = json.loads(resp.read().decode("utf-8"))

        if not geo_data.get("results"):
            return ToolResult(
                success=False,
                message=f"Could not find coordinates for '{loc_clean}'. Please specify a nearby city.",
            )

        res = geo_data["results"][0]
        lat = res["latitude"]
        lon = res["longitude"]
        city_name = res.get("name", loc_clean)
        admin = res.get("admin1", "")
        loc_str = f"{city_name}, {admin}" if admin else city_name

        # 2. Weather & Forecast
        w_url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
            f"&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
            f"&current_weather=true&timezone=auto"
        )
        req2 = urllib.request.Request(w_url, headers={"User-Agent": "ARYA-AI/2.0"})
        with urllib.request.urlopen(req2, timeout=6) as resp2:
            w_data = json.loads(resp2.read().decode("utf-8"))

        daily = w_data.get("daily", {})
        curr = w_data.get("current_weather", {})

        is_tomorrow = any(k in period for k in ("tomorrow", "tmrw", "next day", "upcoming"))

        if is_tomorrow and daily.get("temperature_2m_max") and len(daily["temperature_2m_max"]) > 1:
            high = daily["temperature_2m_max"][1]
            low = daily["temperature_2m_min"][1]
            code = daily.get("weathercode", [0, 0])[1]
            condition = WEATHER_CODES.get(code, "fair weather")
            rain_chance = daily.get("precipitation_probability_max", [0, 0])[1]
            msg = (
                f"Tomorrow in {loc_str}, expect {condition} with a high of {high}C and a low of {low}C. "
                f"Rain probability is {rain_chance}%."
            )
        else:
            curr_temp = curr.get("temperature", "--")
            code = curr.get("weathercode", 0)
            condition = WEATHER_CODES.get(code, "fair weather")
            wind = curr.get("windspeed", "--")
            high = daily.get("temperature_2m_max", [curr_temp])[0]
            low = daily.get("temperature_2m_min", [curr_temp])[0]
            msg = (
                f"Currently in {loc_str}, it is {curr_temp}C with {condition}. "
                f"Today's high is {high}C and low is {low}C, with wind speed at {wind} km/h."
            )

        return ToolResult(success=True, message=msg, detail=str(w_data))

    except Exception as exc:
        print(f"[WEATHER TOOL] Error: {exc}")
        return ToolResult(
            success=False,
            message=f"Could not retrieve weather data for {loc_clean}: {exc}",
            error=str(exc),
        )


def _search_information(params: dict[str, Any]) -> ToolResult:
    """Fetch instant factual knowledge from DuckDuckGo and Wikipedia."""
    query = str(params.get("query", "")).strip()
    if not query:
        return ToolResult(success=False, message="Please specify what you would like to look up.")

    try:
        # 1. Try DuckDuckGo Instant Answer
        ddg_url = (
            f"https://api.duckduckgo.com/?q={urllib.parse.quote_plus(query)}"
            f"&format=json&no_html=1&skip_disambig=1"
        )
        req = urllib.request.Request(ddg_url, headers={"User-Agent": "ARYA-AI/2.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        abstract = data.get("AbstractText", "").strip()
        if abstract:
            source = data.get("AbstractSource", "Web Knowledge")
            return ToolResult(success=True, message=f"{abstract} (Source: {source})")

        # 2. Fallback: Wikipedia Summary API
        wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(query)}"
        req2 = urllib.request.Request(wiki_url, headers={"User-Agent": "ARYA-AI/2.0"})
        with urllib.request.urlopen(req2, timeout=5) as resp2:
            w_json = json.loads(resp2.read().decode("utf-8"))
            extract = w_json.get("extract", "").strip()
            if extract:
                return ToolResult(success=True, message=extract)

        return ToolResult(
            success=True,
            message=f"I found references for '{query}'. You can also ask me specific questions about it.",
        )

    except Exception as exc:
        return ToolResult(
            success=False,
            message=f"Information search for '{query}' encountered an issue: {exc}",
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Tool Registrations
# ---------------------------------------------------------------------------

registry.register(
    schema=ToolSchema(
        name="get_weather",
        description="Get live real-time weather and forecasts for any city or region (e.g. Guntur, Hyderabad, tomorrow's rain, temperature).",
        category=ToolCategory.SYSTEM,
        params=[
            ToolParam("location", ParamType.STRING, "City or region name (default: Guntur)", required=False, default="Guntur"),
            ToolParam("period", ParamType.STRING, "'today' or 'tomorrow'", required=False, default="today"),
        ],
        examples=[
            "what's the weather today",
            "weather tomorrow in Guntur",
            "is it going to rain in Guntur tomorrow",
            "temperature in Hyderabad",
        ],
    ),
    handler=_get_weather,
)

registry.register(
    schema=ToolSchema(
        name="search_information",
        description="Look up instant factual knowledge, explanations, people, places, concepts, or news summaries from the web.",
        category=ToolCategory.BROWSER,
        params=[
            ToolParam("query", ParamType.STRING, "Search query or topic to explain", required=True),
        ],
        examples=[
            "who is Elon Musk",
            "tell me about quantum computing",
            "what is photosynthesis",
            "who founded Apple",
        ],
    ),
    handler=_search_information,
)
