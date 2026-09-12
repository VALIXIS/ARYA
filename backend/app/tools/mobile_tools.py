"""
mobile_tools.py
---------------
Cross-Device Mobile Control Tools for Android & iOS.

Registers:
    android_open_app, android_lock, android_wake, android_volume,
    android_play_media, android_screenshot, analyze_phone_screen, ios_command, connect_wireless_android
"""

import os
from pathlib import Path
from .tool_registry import registry
from .tool_schemas import ToolSchema, ToolCategory, ToolParam, ParamType, ToolResult
from ..android_service import android_bridge
from ..ios_service import ios_bridge
from ..vision_service import analyze_phone_screen

def _android_open_app(params: dict) -> ToolResult:
    app_name = params.get("app_name", "").strip()
    search_query = params.get("search_query")
    res = android_bridge.open_app(app_name, search_query=search_query)
    return ToolResult(
        success=res.get("success", False),
        message=res.get("message", ""),
        detail=str(res)
    )

def _android_lock(params: dict) -> ToolResult:
    res = android_bridge.lock_screen()
    return ToolResult(
        success=res.get("success", False),
        message=res.get("message", ""),
        detail=str(res)
    )

def _android_wake(params: dict) -> ToolResult:
    res = android_bridge.wake_screen()
    return ToolResult(
        success=res.get("success", False),
        message=res.get("message", ""),
        detail=str(res)
    )

def _android_volume(params: dict) -> ToolResult:
    percent = int(params.get("percent") or params.get("level") or 50)
    res = android_bridge.set_volume(percent)
    return ToolResult(
        success=res.get("success", False),
        message=res.get("message", ""),
        detail=str(res)
    )

def _android_play_media(params: dict) -> ToolResult:
    res = android_bridge.media_play_pause()
    return ToolResult(
        success=res.get("success", False),
        message=res.get("message", ""),
        detail=str(res)
    )

def _android_screenshot(params: dict) -> ToolResult:
    out_dir = Path("backend/app/static/screenshots")
    out_dir.mkdir(parents=True, exist_ok=True)
    shot_path = str(out_dir / "phone_latest.png")
    res = android_bridge.take_screenshot(shot_path)
    return ToolResult(
        success=res.get("success", False),
        message=res.get("message", ""),
        detail=shot_path if res.get("success") else str(res)
    )

def _connect_wireless_android(params: dict) -> ToolResult:
    ip = params.get("ip", "").strip()
    raw_port = params.get("port")
    port = int(raw_port) if raw_port is not None and str(raw_port).isdigit() and int(raw_port) > 0 else 0

    if not ip and not port:
        res = android_bridge.auto_discover_and_connect()
    else:
        target_ip = ip or "192.168.31.44"
        res = android_bridge.connect_wireless(target_ip, port)
        if not res.get("success"):
            res = android_bridge.auto_discover_and_connect()

    return ToolResult(
        success=res.get("success", False),
        message=res.get("message", ""),
        detail=str(res)
    )

def _pair_wireless_android(params: dict) -> ToolResult:
    ip = params.get("ip", "").strip() or "192.168.31.44"
    raw_port = params.get("port")
    port = int(raw_port) if raw_port is not None and str(raw_port).isdigit() and int(raw_port) > 0 else 0
    code = str(params.get("code") or params.get("pairing_code") or "").strip()
    res = android_bridge.pair_wireless(ip, port, code)
    return ToolResult(
        success=res.get("success", False),
        message=res.get("message", ""),
        detail=str(res),
    )

def _android_unlock(params: dict) -> ToolResult:
    pin = params.get("pin", "9603").strip()
    res = android_bridge.unlock_screen(pin=pin)
    return ToolResult(
        success=res.get("success", False),
        message=res.get("message", ""),
        detail=str(res)
    )

def _android_play_youtube(params: dict) -> ToolResult:
    query = params.get("query", "").strip()
    search_only = params.get("search_only", False)
    res = android_bridge.play_youtube_video(query, search_only=search_only)
    return ToolResult(
        success=res.get("success", False),
        message=res.get("message", ""),
        detail=str(res)
    )

def _android_open_whatsapp(params: dict) -> ToolResult:
    contact = params.get("contact")
    message = params.get("message")
    res = android_bridge.open_whatsapp(contact=contact, message=message)
    return ToolResult(
        success=res.get("success", False),
        message=res.get("message", ""),
        detail=str(res)
    )

def _ios_command(params: dict) -> ToolResult:
    action = params.get("action", "")
    sub_params = params.get("params", {})
    res = ios_bridge.queue_action(action, sub_params)
    return ToolResult(
        success=res.get("success", False),
        message=f"Queued iOS action '{action}' for Apple Shortcuts.",
        detail=str(res)
    )

# ---------------------------------------------------------------------------
# Registrations
# ---------------------------------------------------------------------------

registry.register(
    schema=ToolSchema(
        name="android_open_app",
        description="Launch an app on the connected Android phone and optionally search inside it (e.g. settings, camera, youtube).",
        category=ToolCategory.DEVICE,
        params=[
            ToolParam("app_name", ParamType.STRING, "App name or package, e.g. 'settings', 'youtube'"),
            ToolParam("search_query", ParamType.STRING, "Optional query to search inside the app", required=False),
        ],
        examples=["open setting in my phone and search for display", "open settings on android"],
    ),
    handler=_android_open_app,
)

registry.register(
    schema=ToolSchema(
        name="android_lock",
        description="Turn off / lock the Android phone screen.",
        category=ToolCategory.DEVICE,
        params=[],
        examples=["lock my phone", "lock android"],
    ),
    handler=_android_lock,
)

registry.register(
    schema=ToolSchema(
        name="android_wake",
        description="Wake up / turn on the Android phone screen.",
        category=ToolCategory.DEVICE,
        params=[],
        examples=["wake up phone", "turn on phone screen"],
    ),
    handler=_android_wake,
)

registry.register(
    schema=ToolSchema(
        name="android_volume",
        description="Set the media volume on the connected Android phone (0-100%).",
        category=ToolCategory.DEVICE,
        params=[ToolParam("percent", ParamType.INTEGER, "Volume percentage (0-100)")],
        examples=["set phone volume to 70%", "phone volume 80"],
    ),
    handler=_android_volume,
)

registry.register(
    schema=ToolSchema(
        name="android_play_media",
        description="Toggle media play/pause on the connected Android phone.",
        category=ToolCategory.DEVICE,
        params=[],
        examples=["pause music on phone", "play song on phone"],
    ),
    handler=_android_play_media,
)

registry.register(
    schema=ToolSchema(
        name="android_screenshot",
        description="Take a real-time screenshot of the Android phone screen.",
        category=ToolCategory.DEVICE,
        params=[],
        examples=["take a screenshot of my phone", "capture phone screen"],
    ),
    handler=_android_screenshot,
)

registry.register(
    schema=ToolSchema(
        name="connect_wireless_android",
        description="Connect to an Android phone over local Wi-Fi using Wireless ADB.",
        category=ToolCategory.DEVICE,
        params=[
            ToolParam("ip", ParamType.STRING, "Phone Wi-Fi IP address, e.g. '192.168.31.44'", required=False, default="192.168.31.44"),
            ToolParam("port", ParamType.INTEGER, "Wireless debugging port, e.g. 33257", required=False, default=33257),
        ],
        examples=["connect phone at 192.168.31.44:33257", "connect wireless adb"],
    ),
    handler=_connect_wireless_android,
)

registry.register(
    schema=ToolSchema(
        name="pair_wireless_android",
        description="Pair an Android phone over Wi-Fi using the 6-digit Wi-Fi pairing code and pairing port from Developer Options.",
        category=ToolCategory.DEVICE,
        params=[
            ToolParam("code", ParamType.STRING, "6-digit pairing code from 'Pair device with pairing code'"),
            ToolParam("port", ParamType.INTEGER, "Pairing port shown in the pairing dialog"),
            ToolParam("ip", ParamType.STRING, "Phone Wi-Fi IP address (default: 192.168.31.44)", required=False, default="192.168.31.44"),
        ],
        examples=["pair phone with code 123456 on port 41235", "pair wireless phone 192.168.31.44 123456"],
    ),
    handler=_pair_wireless_android,
)

registry.register(
    schema=ToolSchema(
        name="ios_command",
        description="Queue a hardware or app command for Apple iPhone/iPad via Apple Shortcuts.",
        category=ToolCategory.DEVICE,
        params=[
            ToolParam("action", ParamType.STRING, "Action name e.g. 'volume', 'open_app', 'flashlight'"),
            ToolParam("params", ParamType.STRING, "JSON or string parameters", required=False),
        ],
        examples=["set iphone volume to 50", "open camera on iphone"],
    ),
    handler=_ios_command,
)

registry.register(
    schema=ToolSchema(
        name="android_unlock",
        description="Unlock the Android phone screen using PIN.",
        category=ToolCategory.DEVICE,
        params=[ToolParam("pin", ParamType.STRING, "Unlock PIN (default: '9603')", required=False, default="9603")],
        examples=["unlock my phone", "unlock phone with 9603", "open my phone"],
    ),
    handler=_android_unlock,
)

registry.register(
    schema=ToolSchema(
        name="android_play_youtube",
        description="Search YouTube and play the video directly on the connected Android phone.",
        category=ToolCategory.DEVICE,
        params=[ToolParam("query", ParamType.STRING, "Song or video name to play on phone")],
        examples=[
            "open youtube on my phone and search for Telugu songs and play the first one",
            "play some telugu songs on my phone",
            "play naa ready on phone",
        ],
    ),
    handler=_android_play_youtube,
)

def _android_call(params: dict) -> ToolResult:
    num = params.get("number")
    if not num:
        return ToolResult(False, "Missing 'number' parameter for call.", data={})
    
    if not android_bridge.is_available():
        return ToolResult(False, "No Android phone connected via ADB.", data={})
    
    res = android_bridge.initiate_call(num)
    return ToolResult(
        success=res.get("success", False),
        message=res.get("message", "Call initiated."),
        data=res
    )

registry.register(
    schema=ToolSchema(
        name="android_call",
        description="Initiate a cellular phone call from the connected Android phone.",
        category=ToolCategory.DEVICE,
        params=[ToolParam("number", ParamType.STRING, "The phone number or contact name to call.", required=True)],
        examples=["call 8328200147", "dial adithya vvit"]
    ),
    handler=_android_call,
)

registry.register(
    schema=ToolSchema(
        name="android_open_whatsapp",
        description="Open WhatsApp on Android phone, optionally navigating to a chat with a specific contact.",
        category=ToolCategory.DEVICE,
        params=[
            ToolParam("contact", ParamType.STRING, "Contact name or phone number", required=False),
            ToolParam("message", ParamType.STRING, "Message text to send to the contact", required=False)
        ],
        examples=[
            "open whatsapp on my phone",
            "message 9603416707 Hii Gud mrng",
        ],
    ),
    handler=_android_open_whatsapp,
)

def _android_analyze_screen(params: dict) -> ToolResult:
    prompt = params.get("prompt", "Analyze this screenshot. What is currently on the screen? Give a concise summary.")
    if not android_bridge.is_available():
        return ToolResult(False, "No Android phone connected.", data={})
    
    res = analyze_phone_screen(prompt)
    return ToolResult(
        success=res.get("success", False),
        message=res.get("message", "Screen analyzed."),
        data=res
    )

registry.register(
    schema=ToolSchema(
        name="analyze_phone_screen",
        description="Take a screenshot of the connected Android phone and analyze it using the Gemini Vision API.",
        category=ToolCategory.DEVICE,
        params=[ToolParam("prompt", ParamType.STRING, "The question to ask about the screen (e.g. 'what is on this screen?').", required=False)],
        examples=["read my screen", "what error is on my phone?"]
    ),
    handler=_android_analyze_screen,
)
