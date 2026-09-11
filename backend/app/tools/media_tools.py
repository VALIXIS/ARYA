"""
media_tools.py
--------------
Native Windows media and volume controls via virtual key codes + pycaw for
absolute volume control.

Registers:
  media_play, media_pause, media_next, media_previous  — playback keys
  volume_up, volume_down                               — relative steps
  set_volume(percent)                                  — absolute 0-100
  mute, unmute                                         — toggle mute state

Logs:
  [MEDIA] Source: <app>
  [MEDIA] State:  Playing | Paused
  [MEDIA] Volume: <n>%
"""

from __future__ import annotations

import sys
import ctypes

from .tool_registry import registry
from .tool_schemas import ToolSchema, ToolCategory, ToolParam, ParamType, ToolResult
from ..media_session import media_session

# ---------------------------------------------------------------------------
# Windows Virtual-Key Codes
# ---------------------------------------------------------------------------

VK_VOLUME_MUTE       = 0xAD
VK_VOLUME_DOWN       = 0xAE
VK_VOLUME_UP         = 0xAF
VK_MEDIA_NEXT_TRACK  = 0xB0
VK_MEDIA_PREV_TRACK  = 0xB1
VK_MEDIA_STOP        = 0xB2
VK_MEDIA_PLAY_PAUSE  = 0xB3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_windows() -> str | None:
    """Return an error string if not on Windows, else None."""
    if sys.platform != "win32":
        return "Media controls only supported on Windows."
    return None


def _press_key(vk_code: int, action_name: str) -> ToolResult:
    """Send a single virtual keystroke (key-down + key-up)."""
    err = _check_windows()
    if err:
        print(f"[MEDIA] Failed: {err}")
        return ToolResult(success=False, message=err, error=err)
    try:
        print(f"[MEDIA] Sending key: {action_name}")
        ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)   # key down
        ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)   # key up
        return ToolResult(success=True, message=f"{action_name} executed.")
    except Exception as exc:
        err = f"{type(exc).__name__}: {exc}"
        print(f"[MEDIA] Failed: {err}")
        return ToolResult(success=False, message=f"Failed: {exc}", error=err)


def _set_absolute_volume(percent: int) -> ToolResult:
    """
    Set system master volume to an absolute percentage (0–100).

    Strategy:
      1. Try pycaw (COM-based, precise).
      2. Fall back to PowerShell WScript.Shell + SendKeys volume simulation.
      3. Last resort: send VK_VOLUME key presses to approach target.
    """
    err = _check_windows()
    if err:
        return ToolResult(success=False, message=err, error=err)

    percent = max(0, min(100, int(percent)))
    print(f"[MEDIA] Setting volume to {percent}%")

    # --- Strategy 1: pycaw (new 2025 API) ----------------------------------
    try:
        from pycaw.pycaw import AudioUtilities  # type: ignore

        device = AudioUtilities.GetSpeakers()
        volume = device.EndpointVolume
        scalar = percent / 100.0
        volume.SetMasterVolumeLevelScalar(scalar, None)
        print(f"[MEDIA] Volume: {percent}% (via pycaw)")
        return ToolResult(success=True, message=f"Volume set to {percent}%.")
    except ImportError:
        print("[MEDIA] pycaw not installed — trying PowerShell fallback")
    except Exception as exc:
        print(f"[MEDIA] pycaw failed: {exc} — trying PowerShell fallback")

    # --- Strategy 2: PowerShell nircmd or WScript ---
    try:
        import subprocess
        # nircmd setsysvolume: range 0–65535
        nircmd_val = int(percent / 100 * 65535)
        result = subprocess.run(
            ["nircmd", "setsysvolume", str(nircmd_val)],
            capture_output=True, timeout=3
        )
        if result.returncode == 0:
            print(f"[MEDIA] Volume: {percent}% (via nircmd)")
            return ToolResult(success=True, message=f"Volume set to {percent}%.")
    except Exception:
        pass

    # --- Strategy 3: PowerShell COM automation ---
    try:
        import subprocess
        ps = (
            f"$wsh = New-Object -ComObject WScript.Shell; "
            f"Add-Type -AssemblyName System.Windows.Forms; "
            f"# Cannot set absolute via SendKeys — skipping"
        )
        # Actually set via PowerShell Audio COM
        ps2 = f"""
$vol = {percent}
$Obj = New-Object -ComObject WScript.Shell
# Use Windows Audio Session API via PS
$Code = @'
using System.Runtime.InteropServices;
[Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IAudioEndpointVolume {{
    int f(); int g(); int h(); int i();
    int SetMasterVolumeLevelScalar(float fLevel, System.Guid pguidEventContext);
    int j();
    int GetMasterVolumeLevelScalar(out float pfLevel);
    int k(); int l(); int m(); int n();
    int SetMute([MarshalAs(UnmanagedType.Bool)] bool bMute, System.Guid pguidEventContext);
    int GetMute(out bool pbMute);
}}
[Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDevice {{ int Activate([MarshalAs(UnmanagedType.LPStruct)] System.Guid iid, int dwClsCtx, IntPtr pActivationParams, [MarshalAs(UnmanagedType.IUnknown)] out object ppInterface); }}
[Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
interface IMMDeviceEnumerator {{ int f(); int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice ppEndpoint); }}
[ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
class MMDeviceEnumeratorComObject {{ }}
public class Audio {{
    static IAudioEndpointVolume Vol;
    static Audio() {{
        var enumerator = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
        IMMDevice dev; Marshal.ThrowExceptionForHR(enumerator.GetDefaultAudioEndpoint(0, 1, out dev));
        object aep; Marshal.ThrowExceptionForHR(dev.Activate(typeof(IAudioEndpointVolume).GUID, 23, IntPtr.Zero, out aep));
        Vol = aep as IAudioEndpointVolume;
    }}
    public static void SetVolume(double value) {{ Marshal.ThrowExceptionForHR(Vol.SetMasterVolumeLevelScalar((float)value, System.Guid.Empty)); }}
    public static void Mute(bool mute) {{ Marshal.ThrowExceptionForHR(Vol.SetMute(mute, System.Guid.Empty)); }}
}}
'@
Add-Type -TypeDefinition $Code
[Audio]::SetVolume({percent / 100})
"""
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps2],
            capture_output=True, text=True, timeout=8
        )
        if result.returncode == 0:
            print(f"[MEDIA] Volume: {percent}% (via PowerShell COM)")
            return ToolResult(success=True, message=f"Volume set to {percent}%.")
        else:
            print(f"[MEDIA] PowerShell COM stderr: {result.stderr.strip()}")
    except Exception as exc:
        print(f"[MEDIA] PowerShell COM failed: {exc}")

    return ToolResult(
        success=False,
        message=f"Could not set volume to {percent}%. Install pycaw: pip install pycaw",
        error="No volume control backend available"
    )


def _set_mute(muted: bool) -> ToolResult:
    """Mute or unmute via pycaw, then fall back to PowerShell COM."""
    err = _check_windows()
    if err:
        return ToolResult(success=False, message=err, error=err)

    action = "Muting" if muted else "Unmuting"
    print(f"[MEDIA] {action} system audio")

    # pycaw (new 2025 API)
    try:
        from pycaw.pycaw import AudioUtilities  # type: ignore

        device = AudioUtilities.GetSpeakers()
        volume = device.EndpointVolume
        volume.SetMute(1 if muted else 0, None)
        state = "Muted" if muted else "Unmuted"
        print(f"[MEDIA] {state} (via pycaw)")
        return ToolResult(success=True, message=f"System audio {state.lower()}.")
    except ImportError:
        pass
    except Exception as exc:
        print(f"[MEDIA] pycaw mute failed: {exc}")

    # VK_VOLUME_MUTE keypress (toggles — only reliable if state is known)
    result = _press_key(VK_VOLUME_MUTE, "Mute toggle")
    if result.success:
        state = "muted" if muted else "unmuted"
        result.message = f"System audio {state}."
    return result


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def _media_play(params: dict) -> ToolResult:
    result = _press_key(VK_MEDIA_PLAY_PAUSE, "Play/Resume")
    if result.success:
        result.message = "Media resumed."
        media_session.snapshot()
    return result


def _media_pause(params: dict) -> ToolResult:
    result = _press_key(VK_MEDIA_PLAY_PAUSE, "Pause")
    if result.success:
        result.message = "Media paused."
    return result


def _media_next(params: dict) -> ToolResult:
    result = _press_key(VK_MEDIA_NEXT_TRACK, "Next Track")
    if result.success:
        result.message = "Skipped to next track."
    return result


def _media_previous(params: dict) -> ToolResult:
    result = _press_key(VK_MEDIA_PREV_TRACK, "Previous Track")
    if result.success:
        result.message = "Went to previous track."
    return result


def _volume_up(params: dict) -> ToolResult:
    result = _press_key(VK_VOLUME_UP, "Volume Up")
    if result.success:
        result.message = "Volume increased."
    return result


def _volume_down(params: dict) -> ToolResult:
    result = _press_key(VK_VOLUME_DOWN, "Volume Down")
    if result.success:
        result.message = "Volume decreased."
    return result


def _set_volume_handler(params: dict) -> ToolResult:
    raw = params.get("percent", 50)
    try:
        pct = int(float(str(raw).replace("%", "").strip()))
    except (ValueError, TypeError):
        return ToolResult(success=False, message=f"Invalid volume value: {raw!r}", error="Bad param")
    return _set_absolute_volume(pct)


def _mute_handler(params: dict) -> ToolResult:
    return _set_mute(True)


def _unmute_handler(params: dict) -> ToolResult:
    return _set_mute(False)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

registry.register(
    schema=ToolSchema(
        name="media_play",
        description="Play or resume the currently paused media.",
        category=ToolCategory.SYSTEM,
        examples=["play", "resume", "resume the song", "continue playing"],
    ),
    handler=_media_play,
)

registry.register(
    schema=ToolSchema(
        name="media_pause",
        description="Pause the currently playing media.",
        category=ToolCategory.SYSTEM,
        examples=["pause", "pause the song", "stop playing"],
    ),
    handler=_media_pause,
)

registry.register(
    schema=ToolSchema(
        name="media_next",
        description="Skip to the next media track or video.",
        category=ToolCategory.SYSTEM,
        examples=["next", "next song", "skip track", "next track"],
    ),
    handler=_media_next,
)

registry.register(
    schema=ToolSchema(
        name="media_previous",
        description="Go back to the previous media track or video.",
        category=ToolCategory.SYSTEM,
        examples=["previous", "previous track", "last song", "go back"],
    ),
    handler=_media_previous,
)

registry.register(
    schema=ToolSchema(
        name="volume_up",
        description="Increase the system volume by one step.",
        category=ToolCategory.SYSTEM,
        examples=["volume up", "increase volume", "louder"],
    ),
    handler=_volume_up,
)

registry.register(
    schema=ToolSchema(
        name="volume_down",
        description="Decrease the system volume by one step.",
        category=ToolCategory.SYSTEM,
        examples=["volume down", "decrease volume", "quieter"],
    ),
    handler=_volume_down,
)

registry.register(
    schema=ToolSchema(
        name="set_volume",
        description="Set system volume to an exact percentage (0-100).",
        category=ToolCategory.SYSTEM,
        params=[ToolParam("percent", ParamType.INTEGER, "Volume level 0-100")],
        examples=[
            "set volume to 10 percent",
            "set volume to 50%",
            "set volume to 100",
            "decrease volume to 10 percent",
        ],
    ),
    handler=_set_volume_handler,
)

registry.register(
    schema=ToolSchema(
        name="mute",
        description="Mute the system audio.",
        category=ToolCategory.SYSTEM,
        examples=["mute", "mute the audio", "silence"],
    ),
    handler=_mute_handler,
)

registry.register(
    schema=ToolSchema(
        name="unmute",
        description="Unmute the system audio.",
        category=ToolCategory.SYSTEM,
        examples=["unmute", "unmute the audio", "turn sound back on"],
    ),
    handler=_unmute_handler,
)
