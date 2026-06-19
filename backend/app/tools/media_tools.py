"""
media_tools.py
--------------
Native Windows media and volume controls via virtual key codes.

Registers: media_play, media_pause, media_next, media_previous, volume_up, volume_down
"""

import sys

from .tool_registry import registry
from .tool_schemas import ToolSchema, ToolCategory, ToolResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Windows Virtual-Key Codes for Media
# https://docs.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3


def _press_key(vk_code: int, action_name: str) -> ToolResult:
    """Send a virtual keystroke on Windows."""
    if sys.platform != "win32":
        err = "Media controls only supported on Windows."
        print(f"[MEDIA] Failed: {err}")
        return ToolResult(success=False, message=err, error=err)

    import ctypes

    try:
        print(f"[MEDIA] {action_name}")
        # Key down
        ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
        # Key up
        ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)
        return ToolResult(success=True, message=f"{action_name} executed.")
    except Exception as exc:
        err = f"{type(exc).__name__}: {exc}"
        print(f"[MEDIA] Failed: {err}")
        return ToolResult(success=False, message=f"Failed to execute {action_name}: {exc}", error=err)

# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def _media_play(_params: dict) -> ToolResult:
    return _press_key(VK_MEDIA_PLAY_PAUSE, "Play")

def _media_pause(_params: dict) -> ToolResult:
    return _press_key(VK_MEDIA_PLAY_PAUSE, "Pause")

def _media_next(_params: dict) -> ToolResult:
    return _press_key(VK_MEDIA_NEXT_TRACK, "Next Track")

def _media_previous(_params: dict) -> ToolResult:
    return _press_key(VK_MEDIA_PREV_TRACK, "Previous Track")

def _volume_up(_params: dict) -> ToolResult:
    return _press_key(VK_VOLUME_UP, "Volume Up")

def _volume_down(_params: dict) -> ToolResult:
    return _press_key(VK_VOLUME_DOWN, "Volume Down")

# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

registry.register(
    schema=ToolSchema(
        name="media_play",
        description="Play or resume the current media.",
        category=ToolCategory.SYSTEM,
        examples=["play", "resume"],
    ),
    handler=_media_play,
)

registry.register(
    schema=ToolSchema(
        name="media_pause",
        description="Pause the currently playing media.",
        category=ToolCategory.SYSTEM,
        examples=["pause", "stop playing"],
    ),
    handler=_media_pause,
)

registry.register(
    schema=ToolSchema(
        name="media_next",
        description="Skip to the next media track or video.",
        category=ToolCategory.SYSTEM,
        examples=["next", "skip track", "next song"],
    ),
    handler=_media_next,
)

registry.register(
    schema=ToolSchema(
        name="media_previous",
        description="Go to the previous media track or video.",
        category=ToolCategory.SYSTEM,
        examples=["previous", "previous track", "last song"],
    ),
    handler=_media_previous,
)

registry.register(
    schema=ToolSchema(
        name="volume_up",
        description="Increase the system volume.",
        category=ToolCategory.SYSTEM,
        examples=["volume up", "increase volume", "louder"],
    ),
    handler=_volume_up,
)

registry.register(
    schema=ToolSchema(
        name="volume_down",
        description="Decrease the system volume.",
        category=ToolCategory.SYSTEM,
        examples=["volume down", "decrease volume", "quieter"],
    ),
    handler=_volume_down,
)
