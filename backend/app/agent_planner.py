"""
agent_planner.py
----------------
Converts a user message into a JSON list of tool calls using the LLM.

The tool list is built dynamically from the registry — never hardcoded.

Output schema (list of objects):
    [
      {"tool": "open_app",      "params": {"app_name": "chrome"}},
      {"tool": "youtube_search","params": {"query": "Telugu songs"}}
    ]

Returns [] if the message is not an actionable command.
"""

from __future__ import annotations

import json
import re

from .ai_service import query_llm
from .tools import registry  # auto-registers all tools on import


# ---------------------------------------------------------------------------
# Fast keyword gate (avoids LLM for pure conversation)
# ---------------------------------------------------------------------------

_ACTION_WORDS = frozenset([
    "open", "launch", "start", "close", "kill", "search", "find",
    "play", "create", "make", "new", "folder", "file", "time",
    "date", "google", "youtube", "website", "browse",
    "pause", "next", "previous", "volume", "mute",
])


def _looks_like_command(text: str) -> bool:
    """Return True if any word in the message is an action keyword."""
    words = set(re.findall(r"\b\w+\b", text.lower()))
    return bool(words & _ACTION_WORDS)


# ---------------------------------------------------------------------------
# Prompt builder — reads tools dynamically from registry
# ---------------------------------------------------------------------------

def _build_system_prompt() -> str:
    # Build per-tool descriptions with param details
    tool_lines = []
    for s in registry.all_schemas():
        if s.params:
            param_desc = ", ".join(
                f'"{p.name}": {p.type.value}{" (optional)" if not p.required else ""}'
                for p in s.params
            )
            tool_lines.append(f'  "{s.name}": {s.description} | params: {{{param_desc}}}')
        else:
            tool_lines.append(f'  "{s.name}": {s.description} | params: {{}}')

    tool_block = "\n".join(tool_lines)

    return (
        "You are an action planner for ARYA, a desktop AI assistant.\n"
        "Convert the user message into a JSON array of tool calls.\n\n"
        "AVAILABLE TOOLS (name: description | params):\n"
        f"{tool_block}\n\n"
        "RULES:\n"
        "1. Return ONLY a raw JSON array — no markdown, no explanation.\n"
        "2. Each item must have exactly 'tool' (string) and 'params' (object) keys.\n"
        "3. Use the EXACT param key names shown above.\n"
        "4. If the message is a question or conversation, return [].\n"
        "5. For tools with no params use {}.\n"
        "6. For compound requests, return multiple items in order.\n\n"
        "EXAMPLES:\n"
        '  User: "open chrome" -> [{"tool": "open_app", "params": {"app_name": "chrome"}}]\n'
        '  User: "close notepad" -> [{"tool": "close_app", "params": {"app_name": "notepad"}}]\n'
        '  User: "search youtube telugu songs" -> [{"tool": "youtube_search", "params": {"query": "telugu songs"}}]\n'
        '  User: "open youtube.com" -> [{"tool": "open_website", "params": {"url": "youtube.com"}}]\n'
        '  User: "create a folder called Projects on Desktop" -> [{"tool": "create_folder", "params": {"path": "Desktop/Projects"}}]\n'
        '  User: "create notes.txt" -> [{"tool": "create_file", "params": {"path": "Desktop/notes.txt", "content": ""}}]\n'
        '  User: "create notes.txt with text hello world" -> [{"tool": "create_file", "params": {"path": "Desktop/notes.txt", "content": "hello world"}}]\n'
        '  User: "what time is it" -> [{"tool": "get_time", "params": {}}]\n'
        '  User: "what is today date" -> [{"tool": "get_date", "params": {}}]\n'
        '  User: "tell me a joke" -> []\n'
        '  User: "open chrome and search youtube telugu songs" -> [{"tool": "open_app", "params": {"app_name": "chrome"}}, {"tool": "youtube_search", "params": {"query": "telugu songs"}}]\n'
    )


# ---------------------------------------------------------------------------
# Unknown Tool Mapping / Alias Resolution
# ---------------------------------------------------------------------------

_ALIAS_TOOLS = {
    "open_settings": {"tool": "open_website", "params": {"url": "ms-settings:"}},
    "settings":      {"tool": "open_website", "params": {"url": "ms-settings:"}},
}

def _resolve_and_validate_tools(plan_data: list[dict]) -> list[dict]:
    """
    Map known hallucinations to valid tools, and drop unknown tools.
    """
    valid = []
    for item in plan_data:
        if not isinstance(item, dict) or "tool" not in item or "params" not in item:
            continue
            
        tool_name = item["tool"]
        params = item["params"]

        # Alias resolution
        if tool_name in _ALIAS_TOOLS:
            print(f"[AGENT] Mapped alias tool: {tool_name!r} -> {_ALIAS_TOOLS[tool_name]}")
            valid.append(_ALIAS_TOOLS[tool_name].copy())
            continue

        # Drop unknown tools
        if not registry.has(tool_name):
            print(f"[AGENT] Dropped unknown tool from plan: {tool_name!r}")
            continue

        valid.append({"tool": tool_name, "params": params})
        
    return valid

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def plan(message: str) -> list[dict]:
    """
    Convert a user message into an ordered list of tool-call dicts.
    Returns [] if no tools apply (caller should fall through to AI).

    Logs:
        [AGENT] Planning: <message>
        [AGENT] Plan generated: <n> step(s)
        [AGENT] No plan — falling back to AI
    """
    if not _looks_like_command(message):
        print(f"[AGENT] No action keywords in: {message!r} — skipping planner")
        return []

    print(f"[AGENT] Planning: {message!r}")
    system_prompt = _build_system_prompt()

    try:
        raw = query_llm(system_prompt, message)
        print(f"[AGENT] LLM raw reply: {raw!r}")

        # Strip markdown fences
        clean = raw.strip()
        for fence in ("```json", "```"):
            if clean.startswith(fence):
                clean = clean[len(fence):]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()

        data = json.loads(clean)

        if not isinstance(data, list):
            print(f"[AGENT] LLM returned non-list: {data!r} — skipping")
            return []

        # Validate and map aliases
        valid = _resolve_and_validate_tools(data)

        if valid:
            print(f"[AGENT] Plan generated: {len(valid)} step(s) -> {[v['tool'] for v in valid]}")
        else:
            print("[AGENT] No valid tool calls in plan — falling back to AI")

        return valid

    except json.JSONDecodeError as exc:
        print(f"[AGENT] JSON parse error: {exc} — raw: {raw!r}")
    except Exception as exc:
        print(f"[AGENT] Error during planning: {type(exc).__name__}: {exc}")

    return []

