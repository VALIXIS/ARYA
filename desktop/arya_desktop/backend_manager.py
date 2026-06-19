"""
backend_manager.py
------------------
Auto-start the ARYA FastAPI backend when the desktop app launches.
"""

import logging
import subprocess
import sys
import time
from pathlib import Path

import requests

from arya_desktop.config import BACKEND_HEALTH_URL, BACKEND_LOG

log = logging.getLogger(__name__)

BACKEND_POLL_INTERVAL = 0.5  # seconds between retries
BACKEND_POLL_TIMEOUT = 15    # max seconds to wait
BACKEND_CONNECT_TIMEOUT = 2  # HTTP request timeout

# Resolve the backend directory relative to the project root.
# Layout: ARYA/desktop/arya_desktop/backend_manager.py → ARYA/backend/
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_DIR = _PROJECT_ROOT / "backend"

# Use the project venv's Python so backend dependencies are available.
_VENV_PYTHON = _PROJECT_ROOT / ".venv" / "Scripts" / "pythonw.exe"

# Fully detach the child process on Windows so closing any console
# window does not terminate it.
_DETACH_FLAGS = (
    subprocess.DETACHED_PROCESS          # 0x00000008 — no inherited console
    | subprocess.CREATE_NEW_PROCESS_GROUP  # 0x00000200 — own process group
    | subprocess.CREATE_NO_WINDOW          # 0x08000000 — no new console window
)


def _is_healthy() -> bool:
    """Return True if the backend is responding to API requests."""
    try:
        resp = requests.get(BACKEND_HEALTH_URL, timeout=BACKEND_CONNECT_TIMEOUT)
        return resp.status_code == 200
    except Exception:
        return False


def _launch_backend() -> subprocess.Popen | None:
    """Start ``uvicorn app.main:app`` as a fully detached background process."""
    try:
        python = str(_VENV_PYTHON) if _VENV_PYTHON.exists() else sys.executable

        log_file = open(BACKEND_LOG, "a", encoding="utf-8")  # noqa: SIM115

        creation_flags = _DETACH_FLAGS if sys.platform == "win32" else 0

        process = subprocess.Popen(
            [python, "-m", "uvicorn", "app.main:app"],
            cwd=str(_BACKEND_DIR),
            stdout=log_file,
            stderr=log_file,
            creationflags=creation_flags,
            close_fds=True,
        )
        log.info(f"[STARTUP] Backend PID: {process.pid}")
        return process
    except Exception as exc:
        log.error("[STARTUP] Failed to launch backend: %s", exc)
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
    log.info("[STARTUP] Checking Backend...")

    if _is_healthy():
        log.info("[STARTUP] Backend already running")
        log.info("[STARTUP] Backend healthy: True")
        return "already_running"

    log.info("[STARTUP] Starting Backend...")
    process = _launch_backend()
    if process is None:
        log.info("[STARTUP] Backend healthy: False")
        return "failed"

    if _wait_until_healthy():
        log.info("[STARTUP] Backend started")
        log.info("[STARTUP] Backend healthy: True")
        return "started"

    log.error("[STARTUP] Backend failed to start")
    log.info("[STARTUP] Backend healthy: False")
    return "failed"
