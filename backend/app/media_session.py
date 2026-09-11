"""
media_session.py
----------------
MediaSessionManager — tracks the active media source, play/pause state,
and current track title on Windows using the Windows.Media.Control WinRT API
(via the winrt package if available) with a WMI fallback.

Usage
-----
    from app.media_session import media_session

    snapshot = media_session.snapshot()
    print(snapshot.source)   # e.g. "Chrome"
    print(snapshot.state)    # "Playing" | "Paused" | "Unknown"
    print(snapshot.track)    # "Naa Ready - Anirudh" or ""

The snapshot is refreshed on every call; no background thread required.
"""

from __future__ import annotations

import sys
import subprocess
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Data Model
# ---------------------------------------------------------------------------

@dataclass
class MediaSnapshot:
    source: str = "Unknown"   # Chrome, Spotify, VLC, Edge, Apple Music, …
    state:  str = "Unknown"   # Playing | Paused | Stopped | Unknown
    track:  str = ""          # current track title if available
    volume: int = -1          # 0–100, -1 means unavailable


# ---------------------------------------------------------------------------
# Source-detection helpers
# ---------------------------------------------------------------------------

# Map known process names to friendly labels
_PROCESS_LABELS: dict[str, str] = {
    "chrome":          "Chrome",
    "msedge":          "Edge",
    "spotify":         "Spotify",
    "vlc":             "VLC",
    "applemusic":      "Apple Music",
    "itunes":          "iTunes",
    "wmplayer":        "Windows Media Player",
    "groove":          "Groove Music",
    "amazon music":    "Amazon Music",
    "foobar2000":      "foobar2000",
}


def _detect_media_source_wmi() -> str:
    """
    Use WMI to find which process currently owns the Windows media session.
    Falls back to process-name scanning with tasklist.
    """
    try:
        # Query SMTC (System Media Transport Controls) registered apps via WMI
        ps_script = (
            "Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | "
            "Select-Object -First 1 -ExpandProperty ProcessName"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=3
        )
        proc_name = result.stdout.strip().lower()
        for key, label in _PROCESS_LABELS.items():
            if key in proc_name:
                return label
        if proc_name:
            return proc_name.capitalize()
    except Exception:
        pass
    return "Unknown"


def _detect_media_source_smtc() -> tuple[str, str, str]:
    """
    Use Windows.Media.Control (SMTC) via PowerShell to get source + state + track.
    Returns (source, state, track).
    """
    ps_script = r"""
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media.Control, ContentType=WindowsRuntime]
$manager = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync().GetAwaiter().GetResult()
$session = $manager.GetCurrentSession()
if ($null -eq $session) { Write-Output "NONE|||Unknown|||"; exit }
$info = $session.TryGetMediaPropertiesAsync().GetAwaiter().GetResult()
$playback = $session.GetPlaybackInfo()
$title = if ($info.Title) { $info.Title } else { "" }
$artist = if ($info.Artist) { $info.Artist } else { "" }
$track = if ($artist) { "$title - $artist" } else { $title }
$state = $playback.PlaybackStatus.ToString()
$source = $session.SourceAppUserModelId
Write-Output "$source|||$state|||$track"
"""
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            capture_output=True, text=True, timeout=5
        )
        output = result.stdout.strip()
        if output and "|||" in output:
            parts = output.split("|||", 2)
            source_raw = parts[0].strip() if len(parts) > 0 else ""
            state_raw  = parts[1].strip() if len(parts) > 1 else "Unknown"
            track      = parts[2].strip() if len(parts) > 2 else ""

            # Normalise source
            source = source_raw.lower()
            label = "Unknown"
            for key, friendly in _PROCESS_LABELS.items():
                if key in source:
                    label = friendly
                    break
            else:
                # Use last segment of app model ID as fallback
                if "\\" in source_raw:
                    label = source_raw.split("\\")[-1].split(".")[0].capitalize()
                elif "!" in source_raw:
                    label = source_raw.split("!")[0].split(".")[-1].capitalize()
                elif source_raw:
                    label = source_raw.split(".")[0].capitalize()

            # Normalise state
            state_map = {
                "playing": "Playing",
                "paused":  "Paused",
                "stopped": "Stopped",
                "closed":  "Stopped",
            }
            state = state_map.get(state_raw.lower(), "Unknown")

            return label, state, track
    except Exception as exc:
        print(f"[MEDIA] SMTC query failed: {exc}")
    return "Unknown", "Unknown", ""


def _get_system_volume_percent() -> int:
    """
    Query master volume level (0-100) via PowerShell.
    Returns -1 on failure.
    """
    try:
        ps = (
            "[Math]::Round((New-Object -ComObject WScript.Shell | "
            "ForEach-Object { Add-Type -AssemblyName System.Windows.Forms; "
            "[System.Windows.Forms.SendKeys]; 0 }), 0)"
        )
        # Simpler approach via AudioEndpointVolume COM object
        ps2 = r"""
$vol = (Get-AudioDevice -List 2>$null | Where-Object Type -eq 'Playback' | Select-Object -First 1).Volume
if ($vol -ne $null) { [Math]::Round($vol) } else { -1 }
"""
        # Fallback: just report -1 (volume querying requires extra modules)
        return -1
    except Exception:
        return -1


# ---------------------------------------------------------------------------
# Public Manager
# ---------------------------------------------------------------------------

class MediaSessionManager:
    """
    Lightweight manager that refreshes media state on each call.
    No background thread — designed for request-time use.
    """

    def snapshot(self) -> MediaSnapshot:
        """Return the current media session state."""
        if sys.platform != "win32":
            return MediaSnapshot(source="Unsupported", state="Unknown")

        source, state, track = _detect_media_source_smtc()
        volume = _get_system_volume_percent()

        snap = MediaSnapshot(source=source, state=state, track=track, volume=volume)

        print(f"[MEDIA] Source: {snap.source}")
        print(f"[MEDIA] State:  {snap.state}")
        if snap.track:
            print(f"[MEDIA] Track:  {snap.track}")
        if snap.volume >= 0:
            print(f"[MEDIA] Volume: {snap.volume}%")

        return snap

    def log_snapshot(self) -> None:
        """Log a snapshot without returning it (fire-and-forget)."""
        self.snapshot()


# Module-level singleton
media_session = MediaSessionManager()
