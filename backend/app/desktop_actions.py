"""
desktop_actions.py
------------------
Handles execution of individual desktop actions and action chains.

Supports: open_application, open_website, search_google, search_youtube, open_folder.
Designed to be extended — add new action types to the handlers dict in execute_action_chain().
"""

import os
import shutil
import subprocess
import urllib.parse
import webbrowser
from pathlib import Path


# --- Known application paths for Windows ---
# Maps lowercase app name to a list of possible executable paths.
# PATH resolution is tried first; these are fallbacks.
APP_PATHS = {
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
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "vscode": [
        str(Path.home() / "AppData" / "Local" / "Programs" / "Microsoft VS Code" / "Code.exe"),
        r"C:\Program Files\Microsoft VS Code\Code.exe",
    ],
    "code": [
        str(Path.home() / "AppData" / "Local" / "Programs" / "Microsoft VS Code" / "Code.exe"),
        r"C:\Program Files\Microsoft VS Code\Code.exe",
    ],
    "explorer": ["explorer.exe"],
    "cmd": ["cmd.exe"],
    "powershell": ["powershell.exe"],
}


def _resolve_executable(target: str) -> str | None:
    """
    Try to resolve a target name to a full executable path.
    Order: shutil.which -> known paths table -> direct path check.
    """
    normalized = target.lower().strip()

    # 1. Try PATH resolution first (e.g. 'chrome', 'code')
    found = shutil.which(normalized) or shutil.which(target)
    if found:
        print(f"[ACTION] Executable found in PATH: {found}")
        return found

    # 2. Try known app table
    candidates = APP_PATHS.get(normalized, [])
    for path in candidates:
        if Path(path).exists():
            print(f"[ACTION] Executable found in known paths: {path}")
            return path

    # 3. Try the target as a literal path
    if Path(target).exists():
        print(f"[ACTION] Executable found as literal path: {target}")
        return target

    print(f"[ACTION] Executable NOT found for target: {target!r}")
    return None


def _open_application(target: str) -> str:
    """Open an application by name or path."""
    print(f"[ACTION] Executing: open_application {target!r}")
    print(f"[ACTION] Searching for executable: {target!r}")

    exe = _resolve_executable(target)
    if exe is None:
        raise FileNotFoundError(f"Could not find executable for '{target}'")

    process = subprocess.Popen(
        [exe],
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
    )
    print(f"[ACTION] Success: opened {exe!r}, PID={process.pid}")
    return f"Opened {target}."


def _open_website(url: str) -> str:
    """Open a website in the default browser."""
    print(f"[ACTION] Executing: open_website {url!r}")
    if not url.startswith("http"):
        url = "https://" + url
    print(f"[ACTION] Opening URL: {url}")
    result = webbrowser.open(url)
    if result:
        print(f"[ACTION] Success: browser opened {url}")
    else:
        print(f"[ACTION] Warning: webbrowser.open returned False for {url}")
    return f"Opened {url}."


def _search_google(query: str) -> str:
    """Search Google in the default browser."""
    print(f"[ACTION] Executing: search_google {query!r}")
    encoded = urllib.parse.quote_plus(query)
    url = f"https://google.com/search?q={encoded}"
    print(f"[ACTION] Final URL: {url}")
    result = webbrowser.open(url)
    print(f"[ACTION] Browser launch result: {result}")
    return f"Searched Google for '{query}'."


def _search_youtube(query: str) -> str:
    """Search YouTube in the default browser."""
    print(f"[ACTION] Executing: search_youtube {query!r}")
    encoded = urllib.parse.quote_plus(query)
    url = f"https://youtube.com/results?search_query={encoded}"
    print(f"[ACTION] Final URL: {url}")
    result = webbrowser.open(url)
    print(f"[ACTION] Browser launch result: {result}")
    return f"Searched YouTube for '{query}'."


def _open_folder(path: str) -> str:
    """Open a folder in File Explorer."""
    print(f"[ACTION] Executing: open_folder {path!r}")
    normalized = path.lower().strip()
    if normalized == "downloads":
        path = str(Path.home() / "Downloads")
    elif normalized == "documents":
        path = str(Path.home() / "Documents")
    elif normalized == "desktop":
        path = str(Path.home() / "Desktop")
    elif normalized in ("home", "~"):
        path = str(Path.home())

    resolved = Path(path)
    if not resolved.exists():
        raise FileNotFoundError(f"Folder does not exist: {path}")

    print(f"[ACTION] Opening folder: {resolved}")
    os.startfile(str(resolved))
    print(f"[ACTION] Success: opened folder {resolved}")
    return f"Opened folder '{path}'."


# Registry of all supported action types.
# To add a new action: define a function above and add it here.
_HANDLERS = {
    "open_application": _open_application,
    "open_website": _open_website,
    "search_google": _search_google,
    "search_youtube": _search_youtube,
    "open_folder": _open_folder,
}


def execute_action_chain(actions: list[dict]) -> str:
    """Execute a list of actions sequentially. Logs every step."""
    print(f"[ACTION] execute_action_chain called with {len(actions)} action(s): {actions}")
    results = []

    for action_obj in actions:
        action_type = action_obj.get("action", "").strip()
        target = action_obj.get("target", "").strip()

        handler = _HANDLERS.get(action_type)
        if handler is None:
            msg = f"Unknown action type: '{action_type}'"
            print(f"[ACTION] Failed: {msg}")
            results.append(msg)
            continue

        try:
            msg = handler(target)
            results.append(msg)
        except FileNotFoundError as e:
            err = f"Failed to {action_type} '{target}': {e}"
            print(f"[ACTION] Failed: {err}")
            results.append(err)
        except Exception as e:
            err = f"Error executing {action_type} '{target}': {type(e).__name__}: {e}"
            print(f"[ACTION] Failed: {err}")
            results.append(err)

    return "\n".join(results)
