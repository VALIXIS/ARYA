"""
startup_manager.py
------------------
Windows startup shortcut management for ARYA Desktop.
"""

import os
import subprocess
import sys
from pathlib import Path

STARTUP_SHORTCUT_NAME = "ARYA Desktop.lnk"


def is_windows() -> bool:
    """Return True when running on Windows."""
    return sys.platform == "win32"


def get_startup_folder() -> Path:
    """Return the Windows Startup folder path."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise OSError("APPDATA environment variable is not set.")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def get_shortcut_path() -> Path:
    """Return the ARYA startup shortcut path."""
    return get_startup_folder() / STARTUP_SHORTCUT_NAME


def get_launch_target() -> tuple[str, str, str]:
    """Return target path, arguments, and working directory for startup.

    Uses ``pythonw.exe`` (windowless interpreter) with ``-m`` module
    invocation so that no console window appears on Windows startup.
    """
    if getattr(sys, "frozen", False):
        target = str(Path(sys.executable).resolve())
        return target, "", str(Path(target).parent)

    # Locate pythonw.exe next to the current python.exe.
    # Avoid aggressive resolve() to prevent escaping the virtual environment.
    python_dir = Path(sys.executable).parent
    pythonw = python_dir / "pythonw.exe"
    target = str(pythonw if pythonw.exists() else sys.executable)

    # Working directory must be the desktop/ package root so that
    # ``-m arya_desktop.main`` resolves correctly.
    desktop_dir = Path(__file__).resolve().parents[1]
    arguments = f"-m arya_desktop.main"
    return target, arguments, str(desktop_dir)


def _powershell_string(value: str) -> str:
    """Escape a value for use in a PowerShell single-quoted string."""
    return "'" + value.replace("'", "''") + "'"


def is_startup_enabled() -> bool:
    """Return True if the startup shortcut exists."""
    if not is_windows():
        return False
    return get_shortcut_path().exists()


def enable_startup() -> None:
    """Create a shortcut in the Windows Startup folder."""
    if not is_windows():
        raise OSError("Startup shortcuts are only supported on Windows.")

    target, arguments, working_dir = get_launch_target()
    shortcut_path = get_shortcut_path()
    shortcut_path.parent.mkdir(parents=True, exist_ok=True)

    command = f"""
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut({_powershell_string(str(shortcut_path))})
$shortcut.TargetPath = {_powershell_string(target)}
$shortcut.Arguments = {_powershell_string(arguments)}
$shortcut.WorkingDirectory = {_powershell_string(working_dir)}
$shortcut.WindowStyle = 1
$shortcut.Description = 'Launch ARYA Desktop on Windows startup'
$shortcut.Save()
""".strip()

    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "Unknown error"
        raise RuntimeError(f"Could not create startup shortcut: {detail}")


def disable_startup() -> None:
    """Remove the ARYA startup shortcut."""
    if not is_windows():
        return

    shortcut_path = get_shortcut_path()
    if shortcut_path.exists():
        shortcut_path.unlink()
