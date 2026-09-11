"""
memory_validator.py
--------------------
Validates whether a memory is worth saving.

Rules:
  1. Category must be in ALLOWED_CATEGORIES (Other is not allowed).
  2. Content must not be a media/tool/desktop command.
  3. Content must not be a temporary or transient fact
     (current location, current time, today's date, weather, etc.).
"""

import re

# The only categories ARYA will persist.
ALLOWED_CATEGORIES = {
    "Identity",
    "Preferences",
    "Education",
    "Interests",
    "Projects",
    "Goals",
    "Career",
    "Devices",
}

# ---------------------------------------------------------------------------
# Blocklist patterns — each is compiled once at import time.
# A memory whose *lowercased* content matches ANY of these is rejected.
# ---------------------------------------------------------------------------

_BLOCKED_PATTERNS: list[re.Pattern] = [re.compile(p, re.IGNORECASE) for p in [
    # ---- Media / playback commands ----------------------------------------
    r"^(pause|play|stop|resume|skip|next|previous|prev)\s*(media|track|song|music|video)?$",
    r"^(next|previous|prev)\s+track$",
    r"^(volume\s*(up|down|mute))$",
    r"^(fast\s*forward|rewind)$",
    r"^shuffle\s*(on|off)?$",
    r"^repeat\s*(on|off|all|one)?$",

    # ---- Desktop / system commands ----------------------------------------
    r"^(open|close|launch|quit|kill|start|restart)\s+\w+",
    r"^(lock|unlock)\s*(screen|computer|pc|laptop)?$",
    r"^(shut\s*down|sleep|hibernate|log\s*off)$",
    r"^(take|capture)\s+a?\s*(screenshot|screen\s*shot)$",
    r"^(type|click|press|scroll|drag)\s+.+",
    r"^(set\s+(alarm|reminder|timer))\b",

    # ---- Temporary location (includes "today") ----------------------------
    r"\btoday\b.*\b(in|at|is)\b",
    r"\b(i'?m?|i\s+am|i\s+was)\s+(currently\s+)?(in|at)\b.+\btoday\b",
    r"^(i'?m?|i\s+am)\s+(currently|right\s+now)\s+(in|at)\b",
    r"^(i'?m?|i\s+am)\s+in\s+\w+\s+(today|now|currently|right\s+now)$",
    r"^(currently|right\s+now)\s+(i'?m?|i\s+am)\s+(in|at)\b",

    # ---- Dates and standalone times ----------------------------------------
    r"^(today|today's\s+date)\s+(is|=)\s*\S+",
    r"^(the\s+)?date\s+(today\s+)?is\b",
    r"^(the\s+)?(current\s+)?time\s+(is|now)\b",
    r"^it'?s?\s+\d{1,2}[:.]\d{2}",          # "It's 10:30"
    r"^\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}$",  # bare date "6/20/2026"

    # ---- Weather -----------------------------------------------------------
    r"^(the\s+)?(current\s+)?weather\b",
    r"\b(weather|temperature|forecast)\s+(is|today|right\s+now)\b",
]]


def _is_blocked(content: str) -> bool:
    """Return True if the content matches any blocked pattern."""
    return any(p.search(content) for p in _BLOCKED_PATTERNS)


def validate_memory(content: str, category: str) -> bool:
    """
    Return True only if the memory should be saved.

    Rejection criteria (returns False):
      - Category is not in ALLOWED_CATEGORIES.
      - Content matches a command or transient-fact pattern.
    """
    if category not in ALLOWED_CATEGORIES:
        print(f"[VALIDATOR] Rejected (bad category={category!r}): {content!r}")
        return False

    if _is_blocked(content):
        print(f"[VALIDATOR] Rejected (blocked pattern): {content!r}")
        return False

    return True
