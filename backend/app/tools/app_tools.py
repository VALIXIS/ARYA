"""
app_tools.py
------------
Application control tools: open and close desktop apps.

Registers 2 tools on import:
    open_app, close_app
"""

import shutil
import subprocess
import sys
from pathlib import Path

from .tool_registry import registry
from .tool_schemas import ToolSchema, ToolCategory, ToolParam, ParamType, ToolResult

import time

# ---------------------------------------------------------------------------
# Known executable paths (Windows fallback table)
# ---------------------------------------------------------------------------

_KNOWN_PATHS: dict[str, list[str]] = {
    "chrome": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        str(Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "Application" / "chrome.exe"),
    ],
    "firefox": [
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
    ],
    "edge": [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ],
    "vscode": [
        str(Path.home() / "AppData" / "Local" / "Programs" / "Microsoft VS Code" / "Code.exe"),
        r"C:\Program Files\Microsoft VS Code\Code.exe",
    ],
    "code": [
        str(Path.home() / "AppData" / "Local" / "Programs" / "Microsoft VS Code" / "Code.exe"),
    ],
    "calculator": ["calc.exe"],
    "notepad":    ["notepad.exe"],
    "paint":      ["mspaint.exe"],
    "cmd":        ["cmd.exe"],
    "explorer":   ["explorer.exe"],
    "spotify": [
        str(Path.home() / "AppData" / "Roaming" / "Spotify" / "Spotify.exe"),
    ],
    "vlc": [
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
    ],
    "word": [
        r"C:\Program Files\Microsoft Office\root\Office16\WINWORD.EXE",
    ],
    "excel": [
        r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE",
    ],
}

# Maps process image names for close_app (lowercase, with .exe)
_PROCESS_NAMES: dict[str, str] = {
    "chrome":      "chrome.exe",
    "firefox":     "firefox.exe",
    "edge":        "msedge.exe",
    "vscode":      "Code.exe",
    "code":        "Code.exe",
    "notepad":     "notepad.exe",
    "calculator":  "calc.exe",
    "explorer":    "explorer.exe",
    "spotify":     "Spotify.exe",
    "vlc":         "vlc.exe",
    "word":        "WINWORD.EXE",
    "excel":       "EXCEL.EXE",
    "paint":       "mspaint.exe",
    "cmd":         "cmd.exe",
}


def _resolve_exe(app_name: str) -> str | None:
    """Return a confirmed executable path for app_name, or None."""
    normalized = app_name.lower().strip()

    # 1. Direct PATH resolution of user input
    found = shutil.which(normalized) or shutil.which(app_name)
    if found:
        return found

    # 2. Known paths table / aliases
    for path_str in _KNOWN_PATHS.get(normalized, []):
        # If the path has no directory separators, it's an alias to resolve via PATH
        if "\\" not in path_str and "/" not in path_str:
            alias_found = shutil.which(path_str)
            if alias_found:
                return alias_found
        elif Path(path_str).exists():
            return path_str

    # 3. Direct path (user might pass full path)
    if Path(app_name).exists():
        return app_name

    return None


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def _open_app(params: dict) -> ToolResult:
    app_name: str = params["app_name"].strip()
    exe = _resolve_exe(app_name)

    if exe is None:
        err = f"Cannot find executable for '{app_name}'"
        return ToolResult(success=False, message=err, error=err)

    try:
        print(f"[ACTION] Launching {exe}")
        proc = subprocess.Popen(
            [exe],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
            close_fds=True,
        )
        print(f"[ACTION] PID {proc.pid}")
        
        # Verify process is alive after 2 seconds
        time.sleep(2.0)
        alive = proc.poll() is None
        ret_code = proc.returncode if not alive else None
        print(f"[ACTION] Process alive: {alive} (returncode: {ret_code})")
        
        # In Windows, many apps (Chrome, Notepad UWP, Calculator UWP) delegate and exit cleanly (returncode 0).
        # Chrome specifically exits with 21 when delegating to an existing instance.
        if alive or ret_code in (0, 21):
            return ToolResult(
                success=True,
                message=f"Opened {app_name}.",
                detail=f"exe={exe!r} PID={proc.pid}",
            )
        else:
            return ToolResult(
                success=False,
                message=f"Opened {app_name} but it immediately closed.",
                error=f"Process exited prematurely with return code {ret_code}",
            )
    except Exception as exc:
        err = f"{type(exc).__name__}: {exc}"
        return ToolResult(success=False, message=f"Failed to open {app_name}: {exc}", error=err)

def _close_app(params: dict) -> ToolResult:
    app_name: str = params["app_name"].strip()
    normalized = app_name.lower().strip()
    process_name = _PROCESS_NAMES.get(normalized, normalized if normalized.endswith(".exe") else normalized + ".exe")

    print(f"[TOOL] close_app: killing {process_name!r}")

    if sys.platform != "win32":
        return ToolResult(success=False, message="close_app only supported on Windows.", error="Not Windows")

    try:
        result = subprocess.run(
            ["taskkill", "/IM", process_name, "/F"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return ToolResult(success=True, message=f"Closed {app_name}.", detail=result.stdout.strip())
        else:
            err = result.stderr.strip() or result.stdout.strip() or f"taskkill exit code {result.returncode}"
            return ToolResult(success=False, message=f"Could not close {app_name}: {err}", error=err)
    except Exception as exc:
        err = f"{type(exc).__name__}: {exc}"
        return ToolResult(success=False, message=f"Failed to close {app_name}: {exc}", error=err)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

registry.register(
    schema=ToolSchema(
        name="open_app",
        description="Open a desktop application by name.",
        category=ToolCategory.APP,
        params=[ToolParam("app_name", ParamType.STRING, "Application name, e.g. 'chrome', 'vscode', 'notepad'")],
        examples=["open chrome", "launch vscode", "open notepad", "start calculator"],
    ),
    handler=_open_app,
)

registry.register(
    schema=ToolSchema(
        name="close_app",
        description="Close (force-quit) a running desktop application by name.",
        category=ToolCategory.APP,
        params=[ToolParam("app_name", ParamType.STRING, "Application name to close, e.g. 'chrome', 'notepad'")],
        examples=["close chrome", "kill notepad", "close vscode"],
    ),
    handler=_close_app,
)
