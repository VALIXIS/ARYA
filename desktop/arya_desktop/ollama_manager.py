"""
ollama_manager.py
-----------------
Auto-start Ollama when the ARYA desktop app launches.
"""

import logging
import os
import shutil
import subprocess
import sys
import time

import requests

from arya_desktop.config import OLLAMA_HEALTH_URL, OLLAMA_LOG

log = logging.getLogger(__name__)

OLLAMA_POLL_INTERVAL = 1.0  # seconds between retries
OLLAMA_POLL_TIMEOUT = 30    # max seconds to wait
OLLAMA_CONNECT_TIMEOUT = 2  # HTTP request timeout

# Default Windows install path for Ollama
_WINDOWS_OLLAMA_PATH = os.path.join(
    os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe"
)

# Fully detach the child process on Windows so closing any console
# window does not terminate it.
_DETACH_FLAGS = (
    subprocess.DETACHED_PROCESS          # 0x00000008 — no inherited console
    | subprocess.CREATE_NEW_PROCESS_GROUP  # 0x00000200 — own process group
    | subprocess.CREATE_NO_WINDOW          # 0x08000000 — no new console window
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
    """Start ``ollama serve`` as a fully detached background process."""
    try:
        log_file = open(OLLAMA_LOG, "a", encoding="utf-8")  # noqa: SIM115

        creation_flags = _DETACH_FLAGS if sys.platform == "win32" else 0

        process = subprocess.Popen(
            [executable, "serve"],
            stdout=log_file,
            stderr=log_file,
            creationflags=creation_flags,
            close_fds=True,
        )
        return process
    except Exception as exc:
        log.error("[STARTUP] Failed to launch Ollama: %s", exc)
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
    log.info("[STARTUP] Checking Ollama...")

    if _is_healthy():
        log.info("[STARTUP] Ollama already running")
        return "already_running"

    executable = _find_ollama()
    if executable is None:
        log.error("[STARTUP] Ollama executable not found")
        return "failed"

    log.info("[STARTUP] Starting Ollama...")
    process = _launch_ollama(executable)
    if process is None:
        return "failed"

    if _wait_until_healthy():
        log.info("[STARTUP] Ollama started")
        return "started"

    log.error("[STARTUP] Ollama failed to start")
    return "failed"
