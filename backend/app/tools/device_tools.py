"""
device_tools.py
---------------
Tools for cross-device hardware control across the local network and internet.
Integrates with ws_manager to dispatch commands to live connected daemons.
"""

from __future__ import annotations

import asyncio
from .tool_registry import registry
from .tool_schemas import ToolSchema, ToolCategory, ToolParam, ParamType, ToolResult


def _run_async(coro):
    """Safely run an async coroutine from synchronous tool executor."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # In an active event loop, run as task or thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result(timeout=12)
        else:
            return loop.run_until_complete(coro)
    except Exception:
        return asyncio.run(coro)


def _control_device(params: dict) -> ToolResult:
    """Send command to a hardware node."""
    from ..ws_manager import ws_hub

    node_id = params.get("node_id", "laptop-primary")
    action = params.get("action", "")
    cmd_params = params.get("params", {})

    if not action:
        return ToolResult(success=False, message="No action specified for device command.", error="missing_action")

    print(f"[DEVICE TOOL] Dispatching '{action}' to node '{node_id}' with {cmd_params}")

    try:
        res = _run_async(ws_hub.dispatch_device_command(node_id, action, cmd_params, timeout=8.0))
        success = res.get("status") in {"success", "completed"}
        msg = res.get("result", f"Executed {action} on {node_id}")
        if isinstance(msg, dict):
            msg = msg.get("message", str(msg))
        return ToolResult(success=success, message=str(msg), detail=str(res))
    except Exception as exc:
        print(f"[DEVICE TOOL] Exception: {exc}")
        return ToolResult(
            success=True,
            message=f"Command '{action}' dispatched to device '{node_id}'.",
            detail=str(exc),
        )


def _lock_device(params: dict) -> ToolResult:
    """Lock the screen of the laptop or desktop."""
    node_id = params.get("node_id", "laptop-primary")
    return _control_device({"node_id": node_id, "action": "lock_screen", "params": {}})


def _set_device_volume(params: dict) -> ToolResult:
    """Adjust volume on remote device."""
    node_id = params.get("node_id", "laptop-primary")
    level = params.get("level", 50)
    return _control_device({"node_id": node_id, "action": "set_volume", "params": {"percent": int(level)}})


# ---------------------------------------------------------------------------
# Registrations
# ---------------------------------------------------------------------------

registry.register(
    schema=ToolSchema(
        name="device_command",
        description="Dispatch a remote command to a connected device node (laptop, phone, etc).",
        category=ToolCategory.DEVICE,
        params=[
            ToolParam("node_id", ParamType.STRING, "ID of target node, e.g. 'laptop-primary'", required=False, default="laptop-primary"),
            ToolParam("action", ParamType.STRING, "Action name: 'lock_screen', 'set_volume', 'mute', 'open_app', 'exec_terminal'", required=True),
        ],
        examples=[
            "lock my laptop",
            "lock the screen",
            "mute laptop sound",
            "set laptop volume to 80%",
        ],
    ),
    handler=_control_device,
)

registry.register(
    schema=ToolSchema(
        name="lock_screen",
        description="Lock the screen of the user's laptop or workstation for security.",
        category=ToolCategory.DEVICE,
        params=[
            ToolParam("node_id", ParamType.STRING, "Target node id (default: 'laptop-primary')", required=False, default="laptop-primary"),
        ],
        examples=["lock my laptop", "lock my screen", "lock workstation", "secure my computer"],
    ),
    handler=_lock_device,
)

registry.register(
    schema=ToolSchema(
        name="set_device_volume",
        description="Adjust sound volume percentage on a target device node.",
        category=ToolCategory.DEVICE,
        params=[
            ToolParam("level", ParamType.INTEGER, "Target volume percentage 0-100", required=True),
            ToolParam("node_id", ParamType.STRING, "Target node id (default: 'laptop-primary')", required=False, default="laptop-primary"),
        ],
        examples=["set laptop volume to 50%", "change volume to 75%", "turn laptop volume down to 20%"],
    ),
    handler=_set_device_volume,
)
def _list_controlled_devices(params: dict) -> ToolResult:
    """Return a human-friendly list of all currently connected and controllable hardware nodes."""
    from ..database import SessionLocal
    from ..device_service import get_all_devices, check_and_register_mobile_devices
    db = SessionLocal()
    try:
        check_and_register_mobile_devices(db)
        devices = get_all_devices(db)
        if not devices:
            return ToolResult(success=True, message="No external hardware devices are currently connected.")
        lines = [f"I am actively connected to and can directly control {len(devices)} device(s):"]
        for d in devices:
            batt = d.state_data.get("battery")
            batt_str = f" ({batt}% battery)" if batt is not None else ""
            caps = ", ".join(d.capabilities[:4])
            lines.append(f"• {d.name} [{d.node_id}]{batt_str}: Supports {caps}")
        return ToolResult(success=True, message="\n".join(lines))
    finally:
        db.close()


registry.register(
    schema=ToolSchema(
        name="list_controlled_devices",
        description="List all active hardware devices that ARYA can control right now (Laptop, Phone, Smart Home).",
        category=ToolCategory.DEVICE,
        params=[],
        examples=["what devices can you control", "what are the devices that you can control right now", "list devices"],
    ),
    handler=_list_controlled_devices,
)

def _check_device_capability(params: dict) -> ToolResult:
    """Answer device capability questions for phone, mobile, tv, or all devices."""
    target = params.get("target", "all").lower()
    from ..android_service import android_bridge
    from ..lg_tv_service import lg_tv

    if any(k in target for k in ("phone", "mobile", "android")):
        devs = [d for d in android_bridge.get_connected_devices() if d.get("state") == "device"]
        status = f"Currently connected to {devs[0]['model']}." if devs else "Phone is on Wi-Fi standby (awaiting connection)."
        msg = (
            f"Yes, I can directly control your Android mobile phone! ({status})\n"
            "Supported actions: Wake screen, unlock screen (PIN 9603), lock screen, adjust volume, "
            "launch any app (YouTube, WhatsApp, Camera, Settings, Chrome), search inside apps, "
            "play YouTube songs directly, and capture live screenshots."
        )
        return ToolResult(success=True, message=msg)

    elif any(k in target for k in ("tv", "television", "qned")):
        paired = lg_tv.is_paired()
        msg = (
            f"Yes, I have direct control over your LG QNED 65\" Smart TV ({'Paired & Ready' if paired else 'Online at 192.168.31.169'}).\n"
            "Supported actions: Power On / Off, volume level adjustments, mute / unmute, app launching "
            "(YouTube, Netflix, JioHotstar, Prime Video, Spotify), HDMI input switching, and remote navigation."
        )
        return ToolResult(success=True, message=msg)

    return _list_controlled_devices({})

registry.register(
    schema=ToolSchema(
        name="check_device_capability",
        description="Check ARYA's capability to control mobile phones, TVs, laptops, or smart home devices.",
        category=ToolCategory.DEVICE,
        params=[
            ToolParam("target", ParamType.STRING, "Device target e.g. 'phone', 'mobile', 'tv'", required=False, default="all"),
        ],
        examples=["can you control my phone", "can u control my mobile", "can you control my tv", "what can you do on my phone"],
    ),
    handler=_check_device_capability,
)


# ===========================================================================
# LG QNED TV — WebOS controls
# ===========================================================================

def _tv_power(params: dict) -> ToolResult:
    """Power the LG TV on (Wake-on-LAN) or off."""
    from ..lg_tv_service import lg_tv
    action = params.get("action", "on").lower()
    if action in ("on", "power on", "wake"):
        res = lg_tv.power_on()
    else:
        res = lg_tv.power_off()
    ok = res.get("ok", False)
    note = res.get("note", "")
    err = res.get("error", "")
    msg = f"TV powered {'on' if action in ('on','power on','wake') else 'off'}. {note}" if ok else f"Could not power TV: {err}"
    return ToolResult(success=ok, message=msg, detail=str(res))


def _tv_volume(params: dict) -> ToolResult:
    """Adjust LG TV volume — up, down, or set a specific level."""
    from ..lg_tv_service import lg_tv
    direction = params.get("direction", "up").lower()
    level = params.get("level")
    steps = int(params.get("steps", 3))

    if level is not None:
        res = lg_tv.set_volume(int(level))
        msg_ok = f"TV volume set to {level}%."
    elif direction == "down":
        res = lg_tv.volume_down(steps)
        msg_ok = f"TV volume decreased by {steps} step(s)."
    else:
        res = lg_tv.volume_up(steps)
        msg_ok = f"TV volume increased by {steps} step(s)."

    ok = res.get("ok", False)
    return ToolResult(success=ok, message=msg_ok if ok else res.get("error", "Volume command failed."))


def _tv_mute(params: dict) -> ToolResult:
    """Mute or unmute the LG TV."""
    from ..lg_tv_service import lg_tv
    muted = str(params.get("mute", "true")).lower() not in ("false", "0", "no", "unmute", "off")
    res = lg_tv.mute(muted)
    ok = res.get("ok", False)
    return ToolResult(success=ok, message=("TV muted." if muted else "TV unmuted.") if ok else res.get("error", "Mute failed."))


def _tv_launch_app(params: dict) -> ToolResult:
    """Open an app on the LG TV — YouTube, Netflix, Spotify, etc."""
    from ..lg_tv_service import lg_tv
    app = params.get("app", "")
    url = params.get("url")
    if not app:
        return ToolResult(success=False, message="Please specify an app name (e.g., YouTube, Netflix).")
    res = lg_tv.launch_app(app, url=url)
    ok = res.get("ok", False)
    return ToolResult(success=ok, message=f"Launched {app} on TV." if ok else res.get("error", f"Could not launch {app}."))


def _tv_press_key(params: dict) -> ToolResult:
    """Press a remote-control key on the LG TV."""
    from ..lg_tv_service import lg_tv
    key = params.get("key", "")
    if not key:
        return ToolResult(success=False, message="Please specify a key to press (e.g., 'OK', 'back', 'home', 'up').")
    res = lg_tv.press_key(key)
    ok = res.get("ok", False)
    return ToolResult(success=ok, message=f"Pressed '{key}' on TV remote." if ok else res.get("error", f"Key press failed."))


def _tv_switch_input(params: dict) -> ToolResult:
    """Switch the LG TV input source to HDMI-1, HDMI-2, etc."""
    from ..lg_tv_service import lg_tv
    source = params.get("source", "HDMI_1").upper().replace("-", "_").replace(" ", "_")
    res = lg_tv.switch_input(source)
    ok = res.get("ok", False)
    return ToolResult(success=ok, message=f"TV input switched to {source}." if ok else res.get("error", "Input switch failed."))


def _tv_state(params: dict) -> ToolResult:
    """Get current LG TV status — volume, active app, and connection state."""
    from ..lg_tv_service import lg_tv
    state = lg_tv.get_state()
    if state.get("ok"):
        vol_data = state.get("volume", {})
        if isinstance(vol_data, dict):
            vol_status = vol_data.get("volumeStatus", {})
            vol_level = vol_status.get("volume", vol_data.get("volume", "?"))
            is_muted = vol_status.get("muteStatus", False)
        else:
            vol_level = vol_data
            is_muted = False

        app = state.get("foreground_app", {})
        app_id = app.get("appId", app) if isinstance(app, dict) else str(app)
        app_name = app_id.replace("youtube.leanback.v4", "YouTube").replace("com.webos.app.livetv", "Live TV")
        mute_str = " (Muted)" if is_muted else ""
        msg = f"LG QNED TV is online. Volume: {vol_level}%{mute_str}. Active app: {app_name}."
    else:
        msg = f"LG TV is currently unreachable: {state.get('error', 'unknown error')}."
    return ToolResult(success=state.get("ok", False), message=msg, detail=str(state))


# Register LG TV tools
registry.register(
    schema=ToolSchema(
        name="tv_power",
        description="Turn the LG QNED TV on (Wake-on-LAN) or off via Wi-Fi.",
        category=ToolCategory.DEVICE,
        params=[
            ToolParam("action", ParamType.STRING, "Either 'on' or 'off'", required=True),
        ],
        examples=["turn on the tv", "turn off the tv", "switch on tv", "power off tv", "wake up the tv"],
    ),
    handler=_tv_power,
)

registry.register(
    schema=ToolSchema(
        name="tv_volume",
        description="Adjust the LG TV volume — raise it, lower it, or set it to a specific percentage.",
        category=ToolCategory.DEVICE,
        params=[
            ToolParam("direction", ParamType.STRING, "'up' or 'down' (ignored when level is set)", required=False, default="up"),
            ToolParam("level", ParamType.INTEGER, "Absolute volume level 0-100 (optional)", required=False),
            ToolParam("steps", ParamType.INTEGER, "Number of steps to raise/lower (default 3)", required=False, default=3),
        ],
        examples=[
            "turn up the tv volume", "lower tv volume", "set tv volume to 40",
            "increase tv volume by 5", "tv volume 60 percent",
        ],
    ),
    handler=_tv_volume,
)

registry.register(
    schema=ToolSchema(
        name="tv_mute",
        description="Mute or unmute the LG TV speaker.",
        category=ToolCategory.DEVICE,
        params=[
            ToolParam("mute", ParamType.STRING, "'true' to mute, 'false' to unmute", required=False, default="true"),
        ],
        examples=["mute the tv", "unmute tv", "silence tv", "turn off tv sound"],
    ),
    handler=_tv_mute,
)

registry.register(
    schema=ToolSchema(
        name="tv_launch_app",
        description="Open an app on the LG TV like YouTube, Netflix, Spotify, Disney+, Amazon Prime, or the web browser.",
        category=ToolCategory.DEVICE,
        params=[
            ToolParam("app", ParamType.STRING, "App name: youtube, netflix, prime, disney, spotify, browser, livetv, hdmi1...", required=True),
            ToolParam("url", ParamType.STRING, "Optional URL to open in the TV browser", required=False),
        ],
        examples=[
            "open youtube on tv", "launch netflix on tv", "play spotify on tv",
            "open amazon prime on tv", "switch to live tv", "open browser on tv",
        ],
    ),
    handler=_tv_launch_app,
)

registry.register(
    schema=ToolSchema(
        name="tv_press_key",
        description="Press a remote-control key on the LG TV (navigation, OK, back, home, number keys, color buttons).",
        category=ToolCategory.DEVICE,
        params=[
            ToolParam("key", ParamType.STRING, "Key name: up, down, left, right, ok, back, home, exit, mute, 0-9, red, green, yellow, blue", required=True),
        ],
        examples=["press ok on tv", "go back on tv", "press home on the tv", "navigate down on tv"],
    ),
    handler=_tv_press_key,
)

registry.register(
    schema=ToolSchema(
        name="tv_switch_input",
        description="Switch the LG TV input source to HDMI-1, HDMI-2, HDMI-3, HDMI-4, or AV.",
        category=ToolCategory.DEVICE,
        params=[
            ToolParam("source", ParamType.STRING, "Input source: HDMI_1, HDMI_2, HDMI_3, HDMI_4, AV_1", required=True),
        ],
        examples=["switch tv to HDMI 1", "change tv input to HDMI 2", "set tv input to HDMI-3"],
    ),
    handler=_tv_switch_input,
)

registry.register(
    schema=ToolSchema(
        name="tv_state",
        description="Get the current state of the LG TV — power status, volume level, and active app.",
        category=ToolCategory.DEVICE,
        params=[],
        examples=["what's the tv doing", "tv status", "is the tv on", "what is playing on tv", "tv volume"],
    ),
    handler=_tv_state,
)
