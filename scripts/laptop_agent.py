"""
Project ARYA — Remote Laptop Node Daemon
-----------------------------------------
Runs in the background on your Windows Laptop (SUBHASH-ASUS).
Maintains a persistent secure WebSocket tunnel to ARYA Cloud (Render).
Allows you to control your laptop, adjust volume, lock screen, and run commands
directly from your phone from anywhere in the world!
"""

import sys
import os
import time
import json
import asyncio
import platform
import subprocess
import websockets

# Target ARYA Cloud Backend WebSocket URL
DEFAULT_WS_URL = "wss://arya-qvbp.onrender.com/ws/devices/laptop-primary"
LOCAL_WS_URL = "ws://localhost:8000/ws/devices/laptop-primary"


def get_system_telemetry():
    """Collect local battery, CPU, and RAM stats."""
    telemetry = {
        "hostname": platform.node(),
        "os": platform.system(),
        "cpu_percent": 0,
        "ram_percent": 0,
        "battery": 100,
        "charging": True
    }
    try:
        import psutil
        telemetry["cpu_percent"] = int(psutil.cpu_percent(interval=None))
        telemetry["ram_percent"] = int(psutil.virtual_memory().percent)
        batt = psutil.sensors_battery()
        if batt:
            telemetry["battery"] = int(batt.percent)
            telemetry["charging"] = bool(batt.power_plugged)
    except Exception:
        pass
    return telemetry


def execute_local_command(action: str, params: dict) -> dict:
    """Execute local actions on this Windows machine."""
    action = action.lower().strip()
    try:
        if action in ("lock", "lock_screen"):
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return {"status": "success", "message": "Laptop screen locked successfully."}

        elif action in ("volume", "set_volume"):
            level = int(params.get("level") or params.get("volume") or params.get("percent") or 50)
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(level / 100.0, None)
            return {"status": "success", "message": f"Laptop volume set to {level}%."}

        elif action in ("mute", "unmute"):
            muted = params.get("muted", True)
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMute(1 if muted else 0, None)
            return {"status": "success", "message": "Laptop muted." if muted else "Laptop unmuted."}

        elif action in ("open_app", "launch_app"):
            app_name = params.get("app_name") or params.get("app") or "notepad"
            subprocess.Popen(["cmd.exe", "/c", f"start {app_name}"], shell=True)
            return {"status": "success", "message": f"Launched '{app_name}' on laptop."}

        elif action in ("run_powershell", "powershell", "shell"):
            cmd = params.get("command", "dir")
            res = subprocess.run(["powershell.exe", "-Command", cmd], capture_output=True, text=True, timeout=10)
            return {"status": "success", "output": res.stdout or res.stderr}

        else:
            return {"status": "error", "message": f"Unknown action '{action}' on laptop."}

    except Exception as exc:
        return {"status": "error", "error": str(exc)}


async def run_agent(server_url: str = DEFAULT_WS_URL):
    """Maintain persistent connection to ARYA Cloud."""
    print("=" * 60)
    print("🚀 Project ARYA — Remote Laptop Node Daemon")
    print(f"📡 Connecting to ARYA Cloud: {server_url}")
    print("=" * 60)

    while True:
        try:
            async with websockets.connect(server_url, ping_interval=20, ping_timeout=10) as ws:
                print("✅ Connected to ARYA Cloud! Laptop is now controllable remotely.")

                # Initial registration packet
                init_data = {
                    "type": "register",
                    "node_id": "laptop-primary",
                    "device_type": "laptop",
                    "name": f"{platform.node()} (Windows Laptop)",
                    "telemetry": get_system_telemetry()
                }
                await ws.send(json.dumps(init_data))

                # Background heartbeat loop
                async def heartbeat():
                    while True:
                        await asyncio.sleep(15)
                        hb = {
                            "type": "heartbeat",
                            "node_id": "laptop-primary",
                            "telemetry": get_system_telemetry()
                        }
                        await ws.send(json.dumps(hb))

                hb_task = asyncio.create_task(heartbeat())

                # Command listener loop
                try:
                    async for msg in ws:
                        try:
                            data = json.loads(msg)
                            cmd_type = data.get("type")
                            if cmd_type == "command":
                                cmd_id = data.get("command_id")
                                action = data.get("action")
                                params = data.get("params", {})
                                print(f"⚡ Received Remote Command: '{action}' with params: {params}")

                                result = execute_local_command(action, params)

                                # Send execution response back to Cloud
                                resp = {
                                    "type": "command_response",
                                    "command_id": cmd_id,
                                    "node_id": "laptop-primary",
                                    "action": action,
                                    "result": result
                                }
                                await ws.send(json.dumps(resp))
                                print(f"✅ Executed and reported: {result}")
                        except Exception as exc:
                            print(f"Error handling command: {exc}")
                finally:
                    hb_task.cancel()

        except Exception as exc:
            print(f"⚠️ Connection lost: {exc}. Reconnecting in 5 seconds...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_WS_URL
    try:
        asyncio.run(run_agent(url))
    except KeyboardInterrupt:
        print("\nDaemon stopped by user.")
