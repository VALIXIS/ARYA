"""
backend_manager.py
------------------
Auto-start the ARYA FastAPI backend when the desktop app launches.
"""

import subprocess
import sys
import time
from pathlib import Path

import requests

from arya_desktop.config import BACKEND_HEALTH_URL

BACKEND_POLL_INTERVAL = 0.5  # seconds between retries
BACKEND_POLL_TIMEOUT = 15    # max seconds to wait
BACKEND_CONNECT_TIMEOUT = 2  # HTTP request timeout

# Resolve the backend directory relative to the project root.
# Layout: ARYA/desktop/arya_desktop/backend_manager.py → ARYA/backend/
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_DIR = _PROJECT_ROOT / "backend"

# Use the project venv's Python so backend dependencies are available.
_VENV_PYTHON = _PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"


def _is_healthy() -> bool:
    """Return True if the backend is responding to API requests."""
    try:
        resp = requests.get(BACKEND_HEALTH_URL, timeout=BACKEND_CONNECT_TIMEOUT)
        return resp.status_code == 200
    except Exception:
        return False


def _launch_backend() -> subprocess.Popen | None:
    """Start ``uvicorn app.main:app`` as a detached background process."""
    try:
        creation_flags = 0
        if sys.platform == "win32":
            creation_flags = subprocess.CREATE_NO_WINDOW

        python = str(_VENV_PYTHON) if _VENV_PYTHON.exists() else sys.executable

        process = subprocess.Popen(
            [python, "-m", "uvicorn", "app.main:app"],
            cwd=str(_BACKEND_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
        )
        return process
    except Exception as exc:
        print(f"[STARTUP] Failed to launch backend: {exc}")
        return None


def _wait_until_healthy() -> bool:
    """Poll the health endpoint until the backend responds or timeout."""
    deadline = time.time() + BACKEND_POLL_TIMEOUT
    while time.time() < deadline:
        if _is_healthy():
            return True
        time.sleep(BACKEND_POLL_INTERVAL)
    return False


def ensure_backend() -> str:
    """Ensure the ARYA backend is running.

    Returns
    -------
    str
        ``"already_running"`` – Backend was already healthy.
        ``"started"``         – Backend was launched and is now healthy.
        ``"failed"``          – Backend could not be started.
    """
    print("[STARTUP] Checking Backend...")

    if _is_healthy():
        print("[STARTUP] Backend already running")
        return "already_running"

    print("[STARTUP] Starting Backend...")
    process = _launch_backend()
    if process is None:
        return "failed"

    if _wait_until_healthy():
        print("[STARTUP] Backend started")
        return "started"

    print("[STARTUP] Backend failed to start")
    return "failed"
