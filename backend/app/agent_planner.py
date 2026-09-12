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
    "play", "create", "make", "write", "note", "desktop", "new", "folder", "file", "time",
    "date", "google", "youtube", "website", "browse", "data",
    "pause", "resume", "next", "previous", "volume", "mute", "unmute",
    "set", "percent", "%", "silence",
    "lock", "unlock", "turn", "off", "on", "light", "lights", "tv",
    "ac", "temp", "temperature", "cool", "heat", "laptop", "device", "devices",
    "phone", "mobile", "android", "hardware", "setting", "settings", "display",
    "dim", "brighten", "screen",
    "weather", "forecast", "rain", "climate", "pair", "connect", "who", "what", "explain", "tell",
    "whatsapp", "message", "msg", "send", "chat", "text", "call", "dial", "read", "analyze", "see",
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
        '  User: "resume the song and decrease volume to 10 percent" -> [{"tool": "media_play", "params": {}}, {"tool": "set_volume", "params": {"percent": 10}}]\n'
        '  User: "set volume to 50%" -> [{"tool": "set_volume", "params": {"percent": 50}}]\n'
        '  User: "mute" -> [{"tool": "mute", "params": {}}]\n'
        '  User: "unmute" -> [{"tool": "unmute", "params": {}}]\n'
        '  User: "play Naa Ready song" -> [{"tool": "youtube_play", "params": {"query": "Naa Ready song"}}]\n'
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

_WEB_APPS: dict[str, str] = {
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
    "linkedin": "https://linkedin.com",
    "amazon": "https://amazon.com",
}


def _generate_file_content(content_spec: str) -> str:
    """Generate dynamic content for files if user requests system/profile data or hello note."""
    spec = content_spec.lower().strip()
    if any(k in spec for k in ("data", "hello note", "note", "profile", "telemetry", "details", "info", "init", "about me", "about you")):
        from datetime import datetime
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Read memories and real devices from DB
        try:
            from .database import SessionLocal
            from . import models, device_service
            db = SessionLocal()
            memories = db.query(models.Memory).all()
            devices = device_service.get_all_devices(db)
            db.close()
        except Exception:
            memories = []
            devices = []

        user_lines = []
        for m in memories:
            user_lines.append(f"  - [{m.category}] {m.content}")
        user_info_str = "\n".join(user_lines) if user_lines else "  - Primary User: Subhash (AIML Student & Creator of ARYA)"

        dev_lines = []
        for d in devices:
            batt = d.state_data.get("battery")
            batt_str = f" | Battery: {batt}%" if batt is not None else ""
            dev_lines.append(f"  - {d.name} ({d.device_type.upper()}) -- Status: {d.status.upper()}{batt_str} [IP: {d.ip_address}]")
        dev_info_str = "\n".join(dev_lines) if dev_lines else "  - SUBHASH-ASUS (Laptop Master Node)\n  - I2302 (Android Mobile Node)"

        return (
            "================================================================================\n"
            "                        PROJECT ARYA -- SYSTEM TELEMETRY & REPORT               \n"
            "================================================================================\n\n"
            "[HELLO NOTE]\n"
            "Hello Subhash!\n"
            "This report was generated autonomously by ARYA directly on your desktop.\n"
            "All systems are operating at peak efficiency, running 100% locally and self-contained\n"
            "with zero cloud dependency. I am ready to assist with full cross-device control.\n\n"
            "--------------------------------------------------------------------------------\n"
            "1. ARYA SYSTEM SPECIFICATIONS\n"
            "--------------------------------------------------------------------------------\n"
            "  - Assistant Name       : ARYA\n"
            "  - System Designation   : Autonomous Personal AI Assistant\n"
            "  - Version              : 2.0.0 OS\n"
            "  - Architecture         : Zero-Latency Deterministic Planner + Local LLM Core\n"
            "  - Local Engine         : Ollama Local (qwen2.5:3b)\n"
            "  - Cloud Dependency     : None (100% Local & Self-Contained, Zero Gemini API)\n"
            "  - Host Machine         : SUBHASH-ASUS (Windows 11)\n"
            "  - Real-Time Pipes      : WebSockets Hub (Port 8000), Local IPC\n\n"
            "--------------------------------------------------------------------------------\n"
            "2. USER PROFILE & MEMORIES (WHAT I KNOW ABOUT YOU)\n"
            "--------------------------------------------------------------------------------\n"
            f"{user_info_str}\n\n"
            "--------------------------------------------------------------------------------\n"
            "3. CONNECTED HARDWARE DEVICES & TELEMETRY\n"
            "--------------------------------------------------------------------------------\n"
            f"{dev_info_str}\n\n"
            "================================================================================\n"
            f"Generated: {now_str} | Target: C:\\Users\\nagas\\Desktop\\ARYA.txt\n"
            "================================================================================\n"
        )
    return content_spec


def _parse_single_intent(clause: str, raw_context: str = "") -> list[dict]:
    """Parse a single action clause into a tool call with 0ms latency."""
    text = clause.strip()
    if not text:
        return []

    # 1. YouTube Play / Music
    # e.g. "play some telugu music in youtube", "play some telugu songs i yooutbe", "play naa ready song", "listen to coldplay"
    m_play = re.search(
        r"^(?:play|listen to)\s+(?:some\s+)?(.+?)(?:\s+(?:in|on|i|at)\s+(?:youtube|yooutbe|yooutub|youtub|yt)|\s+song|\s+music)*$",
        text,
        re.IGNORECASE,
    )
    if m_play and not re.search(r"\b(game|store|on phone)\b", text, re.IGNORECASE):
        query = m_play.group(1).strip()
        # Clean trailing platform tags and noise
        query = re.sub(
            r"\s+(?:in|on|i|at)\s+(?:youtube|yooutbe|yooutub|youtub|yt)\b.*$",
            "",
            query,
            flags=re.IGNORECASE,
        ).strip()
        query = re.sub(r"^some\s+", "", query, flags=re.IGNORECASE).strip()
        if query:
            return [{"tool": "youtube_play", "params": {"query": query}}]

    # 2. Search
    m_yt_search = re.search(r"^search\s+(?:on\s+)?youtube\s+(?:for\s+)?(.+)$", text, re.IGNORECASE)
    if m_yt_search:
        return [{"tool": "youtube_search", "params": {"query": m_yt_search.group(1).strip()}}]

    m_g_search = re.search(r"^(?:search\s+(?:on\s+)?google\s+(?:for\s+)?|google\s+)(.+)$", text, re.IGNORECASE)
    if m_g_search:
        return [{"tool": "google_search", "params": {"query": m_g_search.group(1).strip()}}]

    # 3. File & Folder Creation (Desktop & Local Filesystem)
    m_file = re.search(
        r"(?:(?:on\s+(?:my\s+)?desktop|in\s+desktop)\s+)?"
        r"(?:create|make|write)\s+(?:a\s+)?(?:text\s+)?file\s+"
        r"(?:named\s+as|named|called)?\s*([a-zA-Z0-9_\-\.]+)"
        r"(?:\s+(?:on|in)\s+(?:my\s+)?desktop)?"
        r"(?:\s+(?:and\s+)?(?:then\s+)?(?:write|with|saying|containing)\s+(.+))?",
        text,
        re.IGNORECASE,
    )
    if m_file:
        fname = m_file.group(1).strip()
        # Preserve original casing if present in raw context
        m_case = re.search(r'\b([a-zA-Z0-9_\-]+\.[a-zA-Z0-9]+)\b', raw_context)
        if m_case and m_case.group(1).lower() == fname.lower():
            fname = m_case.group(1)

        raw_content = m_file.group(2).strip() if m_file.group(2) else ""
        content = _generate_file_content(raw_content) if raw_content else ""
        path = f"Desktop/{fname}" if not fname.startswith("Desktop/") else fname
        return [{"tool": "create_file", "params": {"path": path, "content": content}}]

    m_folder = re.search(
        r"(?:(?:on\s+(?:my\s+)?desktop|in\s+desktop)\s+)?"
        r"(?:create|make)\s+(?:a\s+)?folder\s+"
        r"(?:named\s+as|named|called)?\s*([a-zA-Z0-9_\-\.]+)"
        r"(?:\s+(?:on|in)\s+(?:my\s+)?desktop)?",
        text,
        re.IGNORECASE,
    )
    if m_folder:
        fname = m_folder.group(1).strip()
        path = f"Desktop/{fname}" if not fname.startswith("Desktop/") else fname
        return [{"tool": "create_folder", "params": {"path": path}}]

    # 3. Device Listing & Capability Query
    # Handles: "can you control my phone?", "can u control my mobile?", "can you control my tv?",
    # "control my phone?", "what devices can you control?", "list devices"
    is_capability_query = (
        re.search(r"\b(?:can\s+(?:you|u)|are\s+you\s+able\s+to|do\s+you)\b.*?\b(?:control|manage|operate|use|access)\b", raw_context, re.IGNORECASE)
        or re.search(r"^(?:can\s+(?:you|u)\s+)?(?:control|manage)\s+(?:my\s+)?(phone|mobile|android|tv|television|qned)\b\??$", text)
        or re.search(r"\bwhat\s+(?:devices?|hardware)\s+(?:can|do)\s+(?:you|u)\s+control\b", text)
        or re.search(r"\b(what|which|list|show)\b.*\b(devices?|hardware)\b", text)
        or text in {"devices", "connected devices", "list devices", "what can you control", "control my phone", "control my mobile", "control my tv"}
    )
    if is_capability_query:
        combined_ref = (text + " " + raw_context).lower()
        if any(k in combined_ref for k in ("phone", "mobile", "android")):
            return [{"tool": "check_device_capability", "params": {"target": "phone"}}]
        if any(k in combined_ref for k in ("tv", "television", "qned")):
            return [{"tool": "check_device_capability", "params": {"target": "tv"}}]
        return [{"tool": "list_controlled_devices", "params": {}}]

    # 4. Mobile Phone Controls (Android)
    if (
        re.search(r"\b(phone|android|mobile|myphone)\b", text)
        or ("password" in text and "9603" in text)
        or re.search(r"\bunlock\s+(?:my\s+)?(?:phone|mobile|android|device|home|screen)\b", text)
        or text in {"unlock", "unlock phone", "unlock my phone", "unlock mobile"}
    ):
        # Wireless Pairing & Connection
        # e.g. "pair phone with code 123456 on port 41235", "pair phone 123456", "try to connect to my mobile"
        if "pair" in text:
            m_code = re.search(r"\b(\d{6})\b", text)
            m_port = re.search(r"\b(?:port\s+|:)(\d{4,5})\b", text)
            code = m_code.group(1) if m_code else ""
            port = int(m_port.group(1)) if m_port else 0
            m_ip = re.search(r"\b(192\.168\.\d+\.\d+)\b", text)
            ip = m_ip.group(1) if m_ip else "192.168.31.44"
            if code:
                return [{"tool": "pair_wireless_android", "params": {"ip": ip, "port": port, "code": code}}]

        if (
            re.search(r"\b(?:connect|reconnect|try\s+to\s+connect)\b.*?\b(?:phone|android|mobile|device)\b", text)
            or text in {
                "connect phone", "connect android", "connect mobile", "connect my phone", "connect my mobile",
                "reconnect phone", "reconnect mobile", "try to connect to my mobile", "try to connect to my phone",
                "try to connect mobile", "connect to my mobile", "connect to my phone", "connect to mobile", "connect to phone"
            }
        ):
            m_port = re.search(r"\b(?:port\s+|:)(\d{4,5})\b", text)
            port = int(m_port.group(1)) if m_port else 0
            m_ip = re.search(r"\b(192\.168\.\d+\.\d+)\b", text)
            ip = m_ip.group(1) if m_ip else "192.168.31.44"
            return [{"tool": "connect_wireless_android", "params": {"ip": ip, "port": port}}]

        # Unlock phone with PIN (default 9603)
        if (
            re.search(r"\bunlock\b", text)
            or ("password" in text and "9603" in text)
            or re.search(r"\b(?:password|pin)\b.*\b(\d{4,6})\b", text)
            or text in {"open phone", "open my phone", "unlock phone", "unlock my phone", "unlock my home"}
        ) and not any(k in text for k in ("youtube", "whatsapp", "camera", "spotify", "music", "songs", "chat", "setting", "settings")):
            pin_m = re.search(r"\b(\d{4,6})\b", text)
            pin = pin_m.group(1) if pin_m else "9603"
            return [{"tool": "android_unlock", "params": {"pin": pin}}]

        # Screen controls
        if re.search(r"\b(turn\s+off|switch\s+off|lock|sleep)\b", text):
            return [{"tool": "android_lock", "params": {}}]
        if re.search(r"\b(turn\s+on|wake|wake\s+up)\b", text) and not any(k in text for k in ("whatsapp", "youtube", "app", "play", "setting", "settings")):
            return [{"tool": "android_wake", "params": {}}]

        # Plain "open youtube on phone" -> simply launch the YouTube app
        if re.search(r"^(?:open|launch)\s+youtube(?:\s+app)?(?:\s+(?:on|in)\s+(?:my\s+)?(?:phone|android))?$", text.strip()):
            return [{"tool": "android_open_app", "params": {"app_name": "youtube"}}]

        # YouTube song search & playback on phone:
        # e.g. "open youtube on my phone and search for Telugu songs and play the first one",
        # "search for telugu songs on my phone", "play telugu songs on my phone"
        if ("youtube" in text or "video" in text or "song" in text) and any(k in text for k in ("search", "play", "first", "watch")):
            m_yt = re.search(r"(?:search\s+(?:for\s+)?|play\s+(?:some\s+)?)(.+?)(?:\s+and\s+play.*|\s+(?:on|in)\s+(?:my\s+)?phone.*|$)", text, re.IGNORECASE)
            if m_yt:
                query = m_yt.group(1).strip()
                query = re.sub(r"\s+(?:on|in)\s+(?:my\s+)?phone.*$", "", query, flags=re.IGNORECASE).strip()
                query = re.sub(r"\s+and\s+play\s+the\s+first\s+one$", "", query, flags=re.IGNORECASE).strip()
                query = re.sub(r"\b(?:on\s+phone|in\s+phone|mobile|android|youtube)\b", "", query, flags=re.IGNORECASE).strip()
                
                # Check if user specifically wants search results only (didn't ask to play)
                search_only = "search" in text and "play" not in text
                
                if query:
                    return [{"tool": "android_play_youtube", "params": {"query": query, "search_only": search_only}}]

    # 3.5 WhatsApp Control
    if "whatsapp" in text:
        # If it's a very simple command, just open it
        clean_text = re.sub(r"\b(open|launch|on|my|the|phone|mobile|android|whatsapp)\b", "", text).strip()
        if not clean_text:
            return [{"tool": "android_open_whatsapp", "params": {}}]
            
        # For complex conversational WhatsApp commands with numbers and messages,
        # it is safer and much more accurate to let the LLM extract the arguments.
        # So we simply return [] to fall through to the LLM.
        pass

        # Phone Calls
        if re.search(r"\b(call|dial)\b", text):
            m_call = re.search(r"\b(?:call|dial)\s+([a-zA-Z0-9\s]+?)(?:\s+(?:on|in|from)\s+(?:my\s+)?(?:phone|mobile))?$", text, re.IGNORECASE)
            if m_call:
                num = m_call.group(1).strip()
                if num and num not in {"the", "a", "my", "phone", "mobile", "android"}:
                    return [{"tool": "android_call", "params": {"number": num}}]

        # Open app & optional search on phone
        # e.g. "open setting in my phone and search for display", "open settings on phone", "open camera on phone"
        m_phone_app_search = re.search(
            r"(?:open|launch)\s+([a-zA-Z0-9_\-]+)(?:\s+app)?(?:\s+(?:on|in)\s+(?:my\s+)?(?:phone|android))?"
            r"\s+and\s+search\s+(?:for\s+)?(.+)",
            text,
            re.IGNORECASE,
        )
        if m_phone_app_search:
            app_raw = m_phone_app_search.group(1).strip().lower()
            if app_raw in {"setting", "display"}:
                app_raw = "settings"
            query_raw = m_phone_app_search.group(2).strip()
            query_raw = re.sub(r"\s+(?:on|in)\s+(?:my\s+)?(?:phone|android).*$", "", query_raw, flags=re.IGNORECASE).strip()
            return [{"tool": "android_open_app", "params": {"app_name": app_raw, "search_query": query_raw}}]

        m_phone_search_app = re.search(
            r"search\s+(?:for\s+)?(.+?)\s+(?:in|on)\s+([a-zA-Z0-9_\-]+)(?:\s+app)?(?:\s+(?:on|in)\s+(?:my\s+)?(?:phone|android))?",
            text,
            re.IGNORECASE,
        )
        if m_phone_search_app:
            query_raw = m_phone_search_app.group(1).strip()
            app_raw = m_phone_search_app.group(2).strip().lower()
            if app_raw in {"setting", "display"}:
                app_raw = "settings"
            return [{"tool": "android_open_app", "params": {"app_name": app_raw, "search_query": query_raw}}]

        m_phone_app = re.search(
            r"(?:open|launch)\s+([a-zA-Z0-9_\-]+)(?:\s+app)?(?:\s+(?:on|in)\s+(?:my\s+)?(?:phone|android))?",
            text,
            re.IGNORECASE,
        )
        if m_phone_app:
            app_raw = m_phone_app.group(1).strip().lower()
            if app_raw not in {"the", "a", "my", "myphone", "phone", "android", "mobile", "chat", "app"}:
                if app_raw in {"setting", "display"}:
                    app_raw = "settings"
                return [{"tool": "android_open_app", "params": {"app_name": app_raw}}]

        if re.search(r"\b(read|analyze|see)\s+(?:my\s+|the\s+)?screen\b", text):
            prompt = text.replace("read my screen", "").strip()
            if not prompt:
                prompt = "Analyze this screenshot. What is currently on the screen? Give a concise summary."
            return [{"tool": "analyze_phone_screen", "params": {"prompt": prompt}}]

        if re.search(r"\b(screenshot|screen\s+capture|capture\s+screen)\b", text):
            return [{"tool": "android_screenshot", "params": {}}]

        if "volume" in text:
            v_match = re.search(r"\b(\d+)\b", text)
            pct = int(v_match.group(1)) if v_match else 50
            return [{"tool": "android_volume", "params": {"percent": pct}}]

        # STRICT media playback with word boundaries - will NEVER match 'display'
        if re.search(r"\b(play\s+music|pause\s+music|resume\s+music|play\s+media|pause\s+media|pause|resume)\b", text) or text in {"play", "pause"}:
            return [{"tool": "android_play_media", "params": {}}]

    # 5. Smart TV (LG QNED WebOS TV)
    if re.search(r"\b(tv|television|qned)\b", text):
        # Mute / Unmute
        if "unmute" in text or ("sound" in text and "on" in text):
            return [{"tool": "tv_mute", "params": {"mute": "false"}}]
        if "mute" in text or "silence" in text:
            return [{"tool": "tv_mute", "params": {"mute": "true"}}]

        # Volume
        m_tv_vol_set = re.search(r"(?:set|change|put)\s+(?:the\s+)?tv\s+volume\s+(?:to\s+)?(\d+)", text)
        if not m_tv_vol_set:
            m_tv_vol_set = re.search(r"tv\s+volume\s+(?:to\s+)?(\d+)", text)
        if m_tv_vol_set:
            return [{"tool": "tv_volume", "params": {"level": int(m_tv_vol_set.group(1))}}]

        if any(w in text for w in ("increase", "turn up", "raise", "higher", "louder")) or re.search(r"\bvolume\s+up\b", text):
            m_step = re.search(r"\b(?:by\s+)?(\d+)\s+steps?\b", text)
            steps = int(m_step.group(1)) if m_step else 3
            return [{"tool": "tv_volume", "params": {"direction": "up", "steps": steps}}]

        if any(w in text for w in ("decrease", "turn down", "lower", "reduce", "softer")) or re.search(r"\bvolume\s+down\b", text):
            m_step = re.search(r"\b(?:by\s+)?(\d+)\s+steps?\b", text)
            steps = int(m_step.group(1)) if m_step else 3
            return [{"tool": "tv_volume", "params": {"direction": "down", "steps": steps}}]

        # App Launching on TV
        for app in ("youtube", "netflix", "prime", "amazon", "hotstar", "jiohotstar", "disney", "spotify", "browser", "livetv"):
            if app in text and ("open" in text or "launch" in text or "play" in text or "switch" in text or "start" in text):
                return [{"tool": "tv_launch_app", "params": {"app": app}}]

        # Input switching
        m_hdmi = re.search(r"\b(hdmi\s*[1-4]|av\s*1?)\b", text)
        if m_hdmi and ("switch" in text or "input" in text or "change" in text or "to" in text):
            src = m_hdmi.group(1).upper().replace(" ", "_")
            return [{"tool": "tv_switch_input", "params": {"source": src}}]

        # Remote key presses (OK, back, home, exit, arrows)
        if re.search(r"\b(press|click|hit)\s+(ok|enter|back|home|exit|menu|up|down|left|right)\b", text):
            m_key = re.search(r"\b(ok|enter|back|home|exit|menu|up|down|left|right)\b", text)
            return [{"tool": "tv_press_key", "params": {"key": m_key.group(1)}}]

        # Power control
        if re.search(r"\b(turn\s+off|switch\s+off|power\s+off|shut\s+down|sleep)\b", text):
            return [{"tool": "tv_power", "params": {"action": "off"}}]
        if re.search(r"\b(turn\s+on|switch\s+on|power\s+on|wake|start)\b", text):
            return [{"tool": "tv_power", "params": {"action": "on"}}]

        # Status / Inquiry
        if any(w in text for w in ("status", "state", "info", "what is on", "playing", "can you control", "connected")):
            return [{"tool": "tv_state", "params": {}}]

        # Fallback for generic "turn on / off tv"
        action = "off" if "off" in text else "on"
        return [{"tool": "tv_power", "params": {"action": action}}]

    # 6. Lock Screen / Laptop / PC
    if re.search(r"\block\b.*\b(laptop|screen|computer|workstation|pc)\b", text) or text in {"lock", "lock screen"}:
        return [{"tool": "lock_screen", "params": {}}]

    # 7. Web Apps / Websites / URLs / Desktop Apps
    # e.g. "open gmail in a new tab aswell in chrome", "open youtube.com", "open github"
    m_open = re.search(
        r"^(?:open|launch|start|go\s+to)\s+(?:a\s+new\s+tab\s+(?:for|in)\s+)?(.+?)(?:\s+in\s+a\s+new\s+tab)?(?:\s+aswell|\s+as\s+well)?(?:\s+in\s+(?:chrome|browser|edge|firefox))?$",
        text,
    )
    if m_open:
        target = m_open.group(1).strip().lower()
        # Check if known web app
        if target in _WEB_APPS:
            return [{"tool": "open_website", "params": {"url": _WEB_APPS[target]}}]

        # Check if URL or domain
        if re.search(r"^(https?://|[a-zA-Z0-9_\-]+\.(?:com|org|net|io|in|dev|ai|app|co))", target):
            return [{"tool": "open_website", "params": {"url": target}}]

        # Check desktop apps
        if target not in {"the", "a", "it", "this", "light", "lights", "tv", "phone", "ac"} and not target.endswith(" on tv") and not target.endswith(" on phone"):
            return [{"tool": "open_app", "params": {"app_name": target}}]

    # 8. Volume / Mute (Laptop / System)
    if text == "mute":
        return [{"tool": "mute", "params": {}}]
    if text == "unmute":
        return [{"tool": "unmute", "params": {}}]
    vol_match = re.search(r"set (?:laptop )?volume to (\d+)", text)
    if vol_match:
        return [{"tool": "set_volume", "params": {"percent": int(vol_match.group(1))}}]

    # 9. Smart Lights
    if "light" in text or "lights" in text:
        state = "off" if "off" in text else "on"
        room = "living room"
        if "bedroom" in text:
            room = "bedroom"
        elif "kitchen" in text:
            room = "kitchen"
        return [{"tool": "control_lights", "params": {"action": state}}]

    # 9. AC / Temperature
    if re.search(r"\b(ac|air conditioner|climate)\b", text):
        temp_match = re.search(r"\b(\d{2})\b", text)
        temp = int(temp_match.group(1)) if temp_match else 22
        power = "off" if "off" in text else "on"
        return [{"tool": "ac_control", "params": {"temperature": temp, "power": power}}]

    # 10. Time / Date
    if "time" in text and ("what" in text or "tell" in text or text == "time" or "current" in text):
        return [{"tool": "get_time", "params": {}}]

    if "date" in text and ("what" in text or "today" in text or text == "date" or "current" in text):
        return [{"tool": "get_date", "params": {}}]

    # 11. Live Weather & Forecasts
    # e.g. "tell me abt the weather tmrw in guntur", "what is the weather in hyderabad", "weather tomorrow"
    if re.search(r"\b(weather|temperature|forecast|rain|climate)\b", text):
        m_loc = re.search(r"\b(?:in|for|at|around)\s+([a-zA-Z\s]+?)(?:\s+(?:today|tomorrow|tmrw|right now|currently)|$)", text)
        city = "Guntur"
        if m_loc:
            loc_cand = m_loc.group(1).strip()
            loc_cand = re.sub(r"\b(the|my|our|city|town)\b", "", loc_cand, flags=re.IGNORECASE).strip()
            if loc_cand and loc_cand.lower() not in {"today", "tomorrow", "tmrw"}:
                city = loc_cand.title()
        return [{"tool": "get_weather", "params": {"city": city}}]

    # 12. To-Do & Task Management
    if re.search(r"\b(task|tasks|todo|to-do)\b", text):
        if re.search(r"\b(add|create|new|remind)\b", text):
            title = re.sub(r"^(?:add|create|new|remind\s+me\s+to|add\s+to\s+(?:my\s+)?(?:tasks|todo|to-do))\s*", "", text, flags=re.IGNORECASE).strip()
            if title:
                return [{"tool": "add_task", "params": {"title": title}}]
        if re.search(r"\b(list|show|what|get|view)\b", text):
            status = "completed" if "completed" in text or "done" in text else "active"
            return [{"tool": "list_tasks", "params": {"status": status}}]
        if re.search(r"\b(complete|finish|done|check\s*off)\b", text):
            target = re.sub(r"^(?:complete|finish|mark|done|check\s*off)\s+(?:task\s+)?", "", text, flags=re.IGNORECASE).strip()
            if target:
                return [{"tool": "complete_task", "params": {"task_identifier": target}}]
        if re.search(r"\b(delete|remove)\b", text):
            target = re.sub(r"^(?:delete|remove)\s+(?:task\s+)?", "", text, flags=re.IGNORECASE).strip()
            if target:
                return [{"tool": "delete_task", "params": {"task_identifier": target}}]

    # 13. Morning Briefing & Proactive Agenda
    if re.search(r"\b(briefing|morning\s+briefing|start\s+my\s+day|agenda|daily\s+summary)\b", text):
        return [{"tool": "generate_morning_briefing", "params": {}}]

    # 14. Email & Calendar Integrations
    if re.search(r"\b(email|emails|gmail|inbox)\b", text):
        if "outlook" in text:
            return [{"tool": "read_outlook_emails", "params": {}}]
        return [{"tool": "read_gmail", "params": {}}]

    if re.search(r"\b(calendar|schedule|meetings|events)\b", text):
        if "outlook" in text:
            return [{"tool": "get_outlook_calendar", "params": {"days": 1}}]
        return [{"tool": "get_google_calendar", "params": {"days": 1}}]

    # 15. Instant Factual Knowledge / Web Information
    # e.g. "who is elon musk", "what is quantum computing", "tell me about albert einstein", "explain gravity"
    m_info = re.search(r"^(?:who\s+(?:is|was)|what\s+(?:is|was|are)|tell\s+me\s+about|explain)\s+(.+)$", text)
    if m_info and not any(k in text for k in ("weather", "tv", "phone", "pc", "volume", "device", "file", "folder", "app", "time", "date", "ac", "light", "task", "todo", "briefing", "email", "calendar")):
        topic = m_info.group(1).strip()
        topic = re.sub(r"^(?:the|a|an)\s+", "", topic, flags=re.IGNORECASE).strip()
        if topic:
            return [{"tool": "search_information", "params": {"query": topic}}]

    return []


def _match_deterministic_plan(message: str) -> list[dict]:
    """
    High-speed zero-latency deterministic pattern matcher for single and compound commands.
    Decomposes multi-intent phrases ('... and also ...') in <1 millisecond.
    """
    text = message.lower().strip()

    # Strip conversational filler prefixes (Strictly ARYA)
    text = re.sub(
        r"^(?:okay|ok|hey|hi|hello|please|can you|could you|would you|arya)\s*,?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()

    # 1. If command targets the phone, check unified phone action first so it is not fragmented
    if re.search(r"\b(phone|android|mobile|myphone)\b", text) or ("password" in text and "9603" in text):
        direct = _parse_single_intent(text, raw_context=message)
        if direct:
            return direct

    # 2. Check if compound conjunctions exist — split only when followed by a new action keyword or target location
    split_pattern = (
        r"\s+(?:and\s+also|as\s+well\s+as|"
        r"(?:,|;|\band\b)\s+(?=(?:on\s+(?:my\s+)?desktop|in\s+(?:chrome|browser)|"
        r"play|open|launch|start|search|create|make|lock|turn|set|mute|wake|show|list)\b))\s*"
    )
    clauses = [c.strip() for c in re.split(split_pattern, text, flags=re.IGNORECASE) if c.strip()]

    if len(clauses) > 1:
        combined_plan: list[dict] = []
        for clause in clauses:
            res = _parse_single_intent(clause, raw_context=message)
            if res:
                combined_plan.extend(res)

        if combined_plan:
            return combined_plan

    # 3. Direct single intent fallback
    direct = _parse_single_intent(text, raw_context=message)
    if direct:
        return direct

    return []



# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def plan(message: str) -> list[dict]:
    """
    Convert a user message into an ordered list of tool-call dicts.
    Returns [] if no tools apply (caller should fall through to AI).
    """
    if not _looks_like_command(message):
        print(f"[AGENT] No action keywords in: {message!r} — skipping planner")
        return []

    # Fast deterministic pre-check (<1ms routing)
    fast_plan = _match_deterministic_plan(message)
    if fast_plan:
        print(f"[AGENT] Fast-path plan matched: {[v['tool'] for v in fast_plan]}")
        return fast_plan

    # Fast conversational / profile / memory query bypass (<1ms)
    from . import profile_commands, memory_commands
    if profile_commands.detect_profile_query(message) or memory_commands.detect_memory_query(message):
        print(f"[AGENT] Profile/memory query detected: {message!r} — bypassing LLM planning")
        return []

    print(f"[AGENT] Planning with LLM: {message!r}")
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
            return _match_deterministic_plan(message)

        # Validate and map aliases
        valid = _resolve_and_validate_tools(data)

        if valid:
            print(f"[AGENT] Plan generated: {len(valid)} step(s) -> {[v['tool'] for v in valid]}")
            return valid
        else:
            print("[AGENT] No valid tool calls in plan — checking fallback")
            return _match_deterministic_plan(message)

    except json.JSONDecodeError as exc:
        print(f"[AGENT] JSON parse error: {exc} — raw: {raw!r}")
    except Exception as exc:
        print(f"[AGENT] Error during planning: {type(exc).__name__}: {exc}")

    # Final fallback to deterministic patterns
    return _match_deterministic_plan(message)


