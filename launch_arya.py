"""
launch_arya.py
--------------
One-click launcher for Project ARYA.
Opens 3 separate console windows:
  1. Backend  - FastAPI on port 8000
  2. Frontend - Vite PWA on port 5173
  3. Daemon   - Hardware control daemon
Then opens the browser cockpit at http://localhost:5173
"""

import os
import sys
import time
import socket
import subprocess
import webbrowser
from pathlib import Path

ROOT_DIR     = Path(__file__).parent.resolve()
BACKEND_DIR  = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
DAEMON_DIR   = ROOT_DIR / "daemon"

# Prefer .venv python/uvicorn if it exists (more reliable than system python)
VENV_PYTHON   = ROOT_DIR / ".venv" / "Scripts" / "python.exe"
VENV_UVICORN  = ROOT_DIR / ".venv" / "Scripts" / "uvicorn.exe"

PYTHON  = str(VENV_PYTHON)  if VENV_PYTHON.exists()  else sys.executable
UVICORN = str(VENV_UVICORN) if VENV_UVICORN.exists() else None

def log(msg: str):
    print(f"[ARYA] {msg}", flush=True)

def port_open(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False

def wait_for_port(port: int, timeout: float = 35.0, label: str = "") -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if port_open(port):
            return True
        time.sleep(0.6)
    log(f"WARNING: {label} did not come up on port {port} within {timeout}s - continuing anyway.")
    return False

def new_console(title: str, cmd: list, cwd: str) -> subprocess.Popen:
    """Open a command in a new titled Windows console window."""
    inner = " ".join(
        f'"{str(c)}"' if (" " in str(c) or "\\" in str(c)) else str(c)
        for c in cmd
    )
    full = ["cmd.exe", "/c", f"title {title} && {inner}"]
    return subprocess.Popen(full, cwd=cwd, creationflags=subprocess.CREATE_NEW_CONSOLE)

def launch_backend():
    if port_open(8000):
        log("Backend already running on port 8000 - skipping.")
        return
    log("Starting Backend (FastAPI) on http://localhost:8000 ...")
    if UVICORN:
        cmd = [UVICORN, "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    else:
        cmd = [PYTHON, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
    new_console("ARYA Backend - FastAPI :8000", cmd, cwd=str(BACKEND_DIR))
    if wait_for_port(8000, label="Backend"):
        log("Backend is LIVE on port 8000.")

def launch_frontend():
    if port_open(5173):
        log("Frontend already running on port 5173 - skipping.")
        return
    log("Starting Frontend (Vite) on http://localhost:5173 ...")
    npm = "npm.cmd"
    new_console("ARYA Frontend - Vite :5173", [npm, "run", "dev", "--", "--host"], cwd=str(FRONTEND_DIR))
    if wait_for_port(5173, timeout=45, label="Frontend"):
        log("Frontend is LIVE on port 5173.")

def launch_daemon():
    log("Starting ARYA Daemon (Hardware Control Layer) ...")
    daemon_script = DAEMON_DIR / "arya_daemon.py"
    new_console(
        "ARYA Daemon - Hardware Control",
        [PYTHON, str(daemon_script), "--node-id", "laptop-primary", "--server", "http://localhost:8000"],
        cwd=str(ROOT_DIR),
    )
    log("Daemon launched in its own window.")

def connect_phone():
    import shutil
    adb = shutil.which("adb") or str(
        Path.home() / "AppData" / "Local" / "Android" / "Sdk" / "platform-tools" / "adb.exe"
    )
    if adb and Path(adb).exists():
        try:
            subprocess.run([adb, "connect", "192.168.31.44:36399"],
                           capture_output=True, text=True, timeout=5)
            log("ADB phone connection attempted.")
        except Exception:
            pass

def main():
    print()
    print("=" * 58)
    print("   PROJECT ARYA - AUTONOMOUS PERSONAL AI ASSISTANT")
    print("   Launching: Backend | Frontend | Daemon")
    print("=" * 58)
    print()

    launch_backend()
    launch_frontend()
    launch_daemon()
    connect_phone()

    log("Opening browser cockpit ...")
    time.sleep(2)
    webbrowser.open("http://localhost:5173")

    print()
    print("=" * 58)
    print("   ALL SYSTEMS LIVE:")
    print("   Backend   ->  http://localhost:8000")
    print("   Frontend  ->  http://localhost:5173")
    print("   Daemon    ->  Running in separate window")
    print("=" * 58)
    print()
    time.sleep(5)

if __name__ == "__main__":
    main()
