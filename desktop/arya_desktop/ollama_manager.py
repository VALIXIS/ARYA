"""
ollama_manager.py
-----------------
Auto-start Ollama when the ARYA desktop app launches.
"""

import os
import shutil
import subprocess
import sys
import time

import requests

from arya_desktop.config import OLLAMA_HEALTH_URL

OLLAMA_POLL_INTERVAL = 1.0  # seconds between retries
OLLAMA_POLL_TIMEOUT = 30    # max seconds to wait
OLLAMA_CONNECT_TIMEOUT = 2  # HTTP request timeout

# Default Windows install path for Ollama
_WINDOWS_OLLAMA_PATH = os.path.join(
    os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe"
)


def _is_healthy() -> bool:
    """Return True if Ollama is responding to requests."""
    try:
        resp = requests.get(OLLAMA_HEALTH_URL, timeout=OLLAMA_CONNECT_TIMEOUT)
        return resp.status_code == 200
    except Exception:
        return False


def _find_ollama() -> str | None:
    """Locate the Ollama executable on Windows."""
    # 1. Check PATH
    found = shutil.which("ollama")
    if found:
        return found

    # 2. Check default Windows install location
    if os.path.isfile(_WINDOWS_OLLAMA_PATH):
        return _WINDOWS_OLLAMA_PATH

    return None


def _launch_ollama(executable: str) -> subprocess.Popen | None:
    """Start ``ollama serve`` as a detached background process."""
    try:
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NO_WINDOW

        process = subprocess.Popen(
            [executable, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
        )
        return process
    except Exception as exc:
        print(f"[STARTUP] Failed to launch Ollama: {exc}")
        return None


def _wait_until_healthy() -> bool:
    """Poll the health endpoint until Ollama responds or timeout."""
    deadline = time.time() + OLLAMA_POLL_TIMEOUT
    while time.time() < deadline:
        if _is_healthy():
            return True
        time.sleep(OLLAMA_POLL_INTERVAL)
    return False


def ensure_ollama() -> str:
    """Ensure Ollama is running.

    Returns
    -------
    str
        ``"already_running"`` – Ollama was already healthy.
        ``"started"``         – Ollama was launched and is now healthy.
        ``"failed"``          – Ollama could not be started.
    """
    print("[STARTUP] Checking Ollama...")

    if _is_healthy():
        print("[STARTUP] Ollama already running")
        return "already_running"

    executable = _find_ollama()
    if executable is None:
        print("[STARTUP] Ollama executable not found")
        return "failed"

    print("[STARTUP] Starting Ollama...")
    process = _launch_ollama(executable)
    if process is None:
        return "failed"

    if _wait_until_healthy():
        print("[STARTUP] Ollama started")
        return "started"

    print("[STARTUP] Ollama failed to start")
    return "failed"
