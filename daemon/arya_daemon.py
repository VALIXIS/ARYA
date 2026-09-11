"""
arya_daemon.py
--------------
Universal Cross-Device Control Daemon for Project ARYA.
Runs on Windows, macOS, or Linux laptops/workstations.
Connects to ARYA backend over secure WebSocket, registers node telemetry,
and executes hardware actions (volume, screen lock, app launch, shell commands).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import platform
import subprocess
import sys
import urllib.request

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] %(message)s")
logger = logging.getLogger("arya.daemon")


class AryaDeviceDaemon:
    """Hardware control daemon connecting to ARYA's WebSocket gateway."""

    def __init__(self, node_id: str, server_url: str, device_name: str | None = None):
        self.node_id = node_id
        self.server_url = server_url.rstrip("/")
        self.os_type = platform.system().lower()  # windows, darwin, linux
        self.device_name = device_name or f"{platform.node()} ({platform.system()})"
        self.running = True

    def get_system_telemetry(self) -> dict:
        """Gather basic CPU, memory, and battery status."""
        state = {
            "os": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        }
        try:
            import psutil
            state["cpu_percent"] = psutil.cpu_percent(interval=None)
            state["ram_percent"] = psutil.virtual_memory().percent
            batt = psutil.sensors_battery()
            if batt:
                state["battery"] = int(batt.percent)
                state["charging"] = batt.power_plugged
        except Exception:
            state["battery"] = 90
            state["charging"] = True
        return state

    # ------------------------------------------------------------------
    # Hardware Actions
    # ------------------------------------------------------------------

    def lock_screen(self) -> dict:
        """Lock the workstation screen."""
        logger.info("[ACTION] Locking screen...")
        try:
            if self.os_type == "windows":
                subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=True)
            elif self.os_type == "darwin":
                subprocess.run(["pmset", "displaysleepnow"], check=True)
            else:
                subprocess.run(["xdg-screensaver", "lock"], check=True)
            return {"status": "success", "message": f"Screen locked on {self.device_name}."}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def set_volume(self, percent: int) -> dict:
        """Set master audio volume level (0-100)."""
        logger.info(f"[ACTION] Setting volume to {percent}%...")
        percent = max(0, min(100, int(percent)))
        try:
            if self.os_type == "windows":
                # PowerShell audio volume adjustment or nircmd
                ps_script = f"""
                $obj = New-Object -ComObject WScript.Shell
                for ($i=0; $i -lt 50; $i++) {{ $obj.SendKeys([char]174) }}
                $steps = [math]::Round({percent} / 2)
                for ($i=0; $i -lt $steps; $i++) {{ $obj.SendKeys([char]175) }}
                """
                subprocess.run(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script], check=True)
            elif self.os_type == "darwin":
                subprocess.run(["osascript", "-e", f"set volume output volume {percent}"], check=True)
            else:
                subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{percent}%"], check=True)
            return {"status": "success", "message": f"Volume adjusted to {percent}% on {self.device_name}."}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def mute(self) -> dict:
        """Mute sound."""
        return self.set_volume(0)

    def launch_app(self, app_name: str) -> dict:
        """Launch an installed application."""
        logger.info(f"[ACTION] Launching application '{app_name}'...")
        try:
            if self.os_type == "windows":
                os.startfile(app_name) if hasattr(os, "startfile") else subprocess.Popen(["start", app_name], shell=True)
            elif self.os_type == "darwin":
                subprocess.Popen(["open", "-a", app_name])
            else:
                subprocess.Popen([app_name])
            return {"status": "success", "message": f"Launched '{app_name}' successfully."}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def exec_terminal(self, command: str) -> dict:
        """Execute a shell command and capture output."""
        logger.info(f"[ACTION] Executing terminal command: {command!r}")
        try:
            res = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=15,
            )
            return {
                "status": "success" if res.returncode == 0 else "failed",
                "returncode": res.returncode,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip(),
            }
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def handle_command(self, action: str, params: dict) -> dict:
        """Route incoming action request to local hardware handler."""
        if action == "lock_screen":
            return self.lock_screen()
        elif action in {"set_volume", "volume"}:
            level = params.get("percent") or params.get("level") or 50
            return self.set_volume(level)
        elif action == "mute":
            return self.mute()
        elif action in {"launch_app", "open_app"}:
            app = params.get("app_name") or params.get("app") or "notepad"
            return self.launch_app(app)
        elif action in {"exec_terminal", "terminal", "exec"}:
            cmd = params.get("command") or params.get("cmd") or ""
            return self.exec_terminal(cmd)
        else:
            return {"status": "unsupported", "message": f"Action '{action}' not recognized by daemon."}

    # ------------------------------------------------------------------
    # Daemon Event Loop
    # ------------------------------------------------------------------

    async def run(self):
        """Connect to ARYA via WebSocket with auto-reconnect."""
        try:
            import websockets
        except ImportError:
            logger.error("The 'websockets' library is required. Install via: pip install websockets")
            return

        ws_url = f"{self.server_url.replace('http://', 'ws://').replace('https://', 'wss://')}/ws/devices/{self.node_id}"
        logger.info(f"[DAEMON] Starting ARYA Hardware Daemon for node '{self.node_id}'...")
        logger.info(f"[DAEMON] Connecting to: {ws_url}")

        while self.running:
            try:
                async with websockets.connect(ws_url) as ws:
                    logger.info(f"[DAEMON] Connected to ARYA hub! Node ID: {self.node_id}")

                    # Send initial registration frame
                    await ws.send(json.dumps({
                        "type": "heartbeat",
                        "node_id": self.node_id,
                        "name": self.device_name,
                        "state": self.get_system_telemetry(),
                    }))

                    async def heartbeat_loop():
                        while self.running:
                            await asyncio.sleep(20)
                            try:
                                await ws.send(json.dumps({
                                    "type": "heartbeat",
                                    "node_id": self.node_id,
                                    "state": self.get_system_telemetry(),
                                }))
                            except Exception:
                                break

                    hb_task = asyncio.create_task(heartbeat_loop())

                    try:
                        while self.running:
                            msg_str = await ws.recv()
                            data = json.loads(msg_str)
                            msg_type = data.get("type")

                            if msg_type == "command":
                                cmd_id = data.get("command_id")
                                action = data.get("action")
                                params = data.get("params", {})
                                logger.info(f"[DAEMON] Received command: '{action}' (ID: {cmd_id})")

                                # Execute in worker thread
                                loop = asyncio.get_event_loop()
                                result = await loop.run_in_executor(None, self.handle_command, action, params)

                                await ws.send(json.dumps({
                                    "type": "command_result",
                                    "command_id": cmd_id,
                                    "node_id": self.node_id,
                                    "result": result,
                                }))

                    finally:
                        hb_task.cancel()

            except Exception as exc:
                logger.warning(f"[DAEMON] Connection lost ({exc}). Reconnecting in 4 seconds...")
                await asyncio.sleep(4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ARYA Universal Hardware Control Daemon")
    parser.add_argument("--node-id", default="laptop-primary", help="Unique identifier for this device node")
    parser.add_argument("--server", default="http://localhost:8000", help="ARYA Backend server URL")
    parser.add_argument("--name", default=None, help="Display name for this device")
    args = parser.parse_args()

    daemon = AryaDeviceDaemon(node_id=args.node_id, server_url=args.server, device_name=args.name)
    try:
        asyncio.run(daemon.run())
    except KeyboardInterrupt:
        print("\n[DAEMON] Stopped by user.")
