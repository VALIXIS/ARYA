"""
action_planner.py
-----------------
Converts user intent into a chained list of desktop actions.

Two-phase approach to avoid unnecessary LLM calls:
1. FAST: rule-based pattern matching for known simple commands.
2. SLOW: LLM call for complex/compound commands.
"""

import json
import re

from .ai_service import query_llm

print("[BOOT] action_planner loaded")

# --- Simple rule-based patterns (matched before LLM call) ---
# Avoids LLM overhead for common single-action commands.
# (regex, action_type, target_group_index or None for static target)
SIMPLE_RULES = [
    # open <app>
    (r"^open\s+(chrome|google chrome)$",        "open_application", "chrome"),
    (r"^open\s+(firefox)$",                      "open_application", "firefox"),
    (r"^open\s+(edge|microsoft edge)$",          "open_application", "edge"),
    (r"^open\s+(vscode|vs code|visual studio)$", "open_application", "vscode"),
    (r"^open\s+(notepad)$",                      "open_application", "notepad"),
    (r"^open\s+(calculator|calc)$",              "open_application", "calculator"),
    (r"^open\s+(explorer|file explorer)$",       "open_application", "explorer"),
    # open <website>
    (r"^open\s+(?:www\.)?youtube(?:\.com)?$",    "open_website", "https://youtube.com"),
    (r"^open\s+(?:www\.)?google(?:\.com)?$",     "open_website", "https://google.com"),
    (r"^open\s+(?:www\.)?github(?:\.com)?$",     "open_website", "https://github.com"),
    (r"^open\s+(https?://\S+)$",                 "open_website", 1),   # group 1 = url
    # search <query>
    (r"^(?:google|search google(?:\s+for)?)\s+(.+)$",  "search_google",  1),
    (r"^search youtube(?:\s+for)?\s+(.+)$",            "search_youtube", 1),
    # open folder
    (r"^open\s+(?:my\s+)?(downloads|documents|desktop|home)(?:\s+folder)?$", "open_folder", 1),
]


def _try_simple_rules(message: str) -> list[dict]:
    """
    Check message against simple rule patterns.
    Returns a list with one action dict if matched, else empty list.
    """
    lower = message.lower().strip()
    for pattern, action_type, target_spec in SIMPLE_RULES:
        match = re.match(pattern, lower, re.IGNORECASE)
        if match:
            # target_spec is either a static string or a group index (int)
            if isinstance(target_spec, int):
                target = match.group(target_spec).strip()
            else:
                target = target_spec
            actions = [{"action": action_type, "target": target}]
            print(f"[ACTION] Simple rule matched: {pattern!r} -> {actions}")
            return actions
    return []


# --- Keywords to trigger LLM planner ---
ACTION_KEYWORDS = ["open", "launch", "search", "find", "play", "start"]

PLANNER_SYSTEM_PROMPT = (
    "You are a desktop action planner. Convert the user's intent into an ordered list of desktop actions.\n"
    "Supported action types: open_website, search_google, search_youtube, open_application, open_folder.\n\n"
    "Rules:\n"
    "1. Return ONLY a JSON array of action objects.\n"
    "2. Each object must have exactly two keys: 'action' and 'target'.\n"
    "3. If no desktop action is needed (e.g. it is a question), return exactly: []\n"
    "4. No markdown, no explanation, no extra text — just the JSON array.\n\n"
    "Examples:\n"
    "User: Open Chrome and search YouTube Telugu songs\n"
    "Response: [{\"action\": \"open_application\", \"target\": \"chrome\"}, "
    "{\"action\": \"search_youtube\", \"target\": \"Telugu songs\"}]\n\n"
    "User: Open Google and search Python tutorials\n"
    "Response: [{\"action\": \"search_google\", \"target\": \"Python tutorials\"}]\n\n"
    "User: What is Python?\n"
    "Response: []"
)


def _might_be_action(text: str) -> bool:
    """Lightweight keyword filter — avoids LLM calls for normal chat messages."""
    lower_text = text.lower()
    return any(keyword in lower_text for keyword in ACTION_KEYWORDS)


def plan_actions(message: str) -> list[dict]:
    """
    Parse a user message into a list of desktop actions.
    Returns empty list if no actions are detected or an error occurs.
    """
    # Phase 1: fast rule-based matching
    simple = _try_simple_rules(message)
    if simple:
        print(f"[ACTION] Rule-based plan: {simple}")
        return simple

    # Phase 2: LLM for compound/complex commands
    if not _might_be_action(message):
        print(f"[ACTION] No action keywords in: {message!r}")
        return []

    print(f"[ACTION] Planner called (LLM) for: {message!r}")

    try:
        raw_reply = query_llm(PLANNER_SYSTEM_PROMPT, message)
        print(f"[ACTION] LLM raw reply: {raw_reply!r}")

        clean = raw_reply.strip()
        for fence in ("```json", "```"):
            if clean.startswith(fence):
                clean = clean[len(fence):]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()

        data = json.loads(clean)
        if isinstance(data, list) and len(data) > 0:
            print(f"[ACTION] Planned steps: {data}")
            return data

        print(f"[ACTION] LLM returned empty list — treating as normal chat")

    except json.JSONDecodeError as e:
        print(f"[ACTION] JSON parse error: {e} — raw reply: {raw_reply!r}")
    except Exception as e:
        print(f"[ACTION] Unexpected error: {e}")

    return []
