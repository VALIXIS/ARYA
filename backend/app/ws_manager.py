"""
ws_manager.py
-------------
Real-time bi-directional WebSocket hub for Project ARYA.
Bridges Web/PWA clients, 3D interactive core, agent thought streams,
and remote hardware/IoT device daemons across the local network and internet.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from fastapi import WebSocket

logger = logging.getLogger("arya.websocket")


def _execute_local_host_action(action: str, params: dict) -> dict:
    """Execute hardware actions directly on this host machine using native OS APIs."""
    import platform
    import subprocess
    import os

    os_type = platform.system().lower()
    logger.info(f"[LOCAL HOST EXEC] Executing '{action}' with params: {params}")

    if action in {"lock_screen", "lock"}:
        try:
            if os_type == "windows":
                subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], check=True)
            elif os_type == "darwin":
                subprocess.run(["pmset", "displaysleepnow"], check=True)
            else:
                subprocess.run(["xdg-screensaver", "lock"], check=True)
            return {"status": "success", "result": "Workstation screen locked successfully."}
        except Exception as exc:
            return {"status": "error", "result": f"Could not lock screen: {exc}"}

    elif action in {"set_volume", "volume"}:
        level = params.get("percent") or params.get("level") or params.get("volume") or 50
        level = max(0, min(100, int(level)))
        try:
            if os_type == "windows":
                try:
                    import pythoncom
                    pythoncom.CoInitialize()
                    from pycaw.pycaw import AudioUtilities
                    speakers = AudioUtilities.GetSpeakers()
                    vol_ctrl = speakers.EndpointVolume
                    vol_ctrl.SetMasterVolumeLevelScalar(level / 100.0, None)
                    pythoncom.CoUninitialize()
                    return {"status": "success", "result": f"Host volume set to {level}%."}
                except Exception as pycaw_err:
                    logger.warning(f"[VOLUME] pycaw control error: {pycaw_err}")
                ps_script = f"""
                $Code = @'
                using System;
                using System.Runtime.InteropServices;
                [Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
                interface IAudioEndpointVolume {{
                    int f(); int g(); int h(); int j();
                    int SetMasterVolumeLevelScalar(float fLevel, System.Guid pguidEventContext);
                }}
                [Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
                interface IMMDevice {{ int Activate([MarshalAs(UnmanagedType.LPStruct)] System.Guid iid, int dwClsCtx, IntPtr pActivationParams, [MarshalAs(UnmanagedType.IUnknown)] out object ppInterface); }}
                [Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
                interface IMMDeviceEnumerator {{ int f(); int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice ppEndpoint); }}
                [ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
                class MMDeviceEnumeratorComObject {{ }}
                public class Audio {{
                    static IAudioEndpointVolume Vol;
                    static Audio() {{
                        var enumerator = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
                        IMMDevice dev; enumerator.GetDefaultAudioEndpoint(0, 1, out dev);
                        object aep; dev.Activate(typeof(IAudioEndpointVolume).GUID, 23, IntPtr.Zero, out aep);
                        Vol = aep as IAudioEndpointVolume;
                    }}
                    public static void SetVolume(double value) {{ Vol.SetMasterVolumeLevelScalar((float)value, System.Guid.Empty); }}
                }}
                '@
                Add-Type -TypeDefinition $Code -ErrorAction SilentlyContinue
                [Audio]::SetVolume({level / 100})
                """
                subprocess.run(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script], check=True)
            elif os_type == "darwin":
                subprocess.run(["osascript", "-e", f"set volume output volume {level}"], check=True)
            else:
                subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{level}%"], check=True)
            return {"status": "success", "result": f"System volume set to {level}%."}
        except Exception as exc:
            return {"status": "error", "result": f"Could not set volume: {exc}"}

    elif action == "mute":
        return _execute_local_host_action("set_volume", {"level": 0})

    elif action in {"launch_app", "open_app"}:
        app_name = params.get("app_name") or params.get("app") or "notepad"
        try:
            if os_type == "windows":
                os.startfile(app_name) if hasattr(os, "startfile") else subprocess.Popen(["start", app_name], shell=True)
            elif os_type == "darwin":
                subprocess.Popen(["open", "-a", app_name])
            else:
                subprocess.Popen([app_name])
            return {"status": "success", "result": f"Launched application '{app_name}'."}
        except Exception as exc:
            return {"status": "error", "result": f"Could not launch app: {exc}"}

    elif action in {"exec_terminal", "terminal", "exec"}:
        cmd = params.get("command") or params.get("cmd") or ""
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            return {
                "status": "success" if res.returncode == 0 else "failed",
                "result": res.stdout.strip() or res.stderr.strip() or f"Exited with code {res.returncode}",
            }
        except Exception as exc:
            return {"status": "error", "result": str(exc)}

    return {"status": "success", "result": f"Action '{action}' processed on local host."}


class WebSocketManager:

    """Manages active WebSockets for Frontend Clients and Device Node Daemons."""

    def __init__(self):
        # Frontend UI clients: set of WebSocket connections
        self.active_clients: set[WebSocket] = set()

        # Connected Device Daemons: dict of node_id -> WebSocket
        self.device_nodes: dict[str, WebSocket] = {}

        # Pending command responses: dict of command_id -> asyncio.Future
        self._pending_commands: dict[str, asyncio.Future] = {}

    # ------------------------------------------------------------------
    # Client Management (Frontend / 3D Core / Mobile PWA)
    # ------------------------------------------------------------------

    async def connect_client(self, websocket: WebSocket) -> None:
        """Register a new frontend client."""
        await websocket.accept()
        self.active_clients.add(websocket)
        logger.info(f"[WS] Client connected. Total active clients: {len(self.active_clients)}")
        # Send welcome & system status frame
        await websocket.send_json({
            "type": "system_status",
            "status": "connected",
            "connected_devices": list(self.device_nodes.keys()),
            "timestamp": asyncio.get_event_loop().time(),
        })

    def disconnect_client(self, websocket: WebSocket) -> None:
        """Unregister a frontend client."""
        self.active_clients.discard(websocket)
        logger.info(f"[WS] Client disconnected. Remaining: {len(self.active_clients)}")

    async def broadcast_to_clients(self, message: dict[str, Any]) -> None:
        """Broadcast an event payload to all connected frontend clients."""
        if not self.active_clients:
            return
        dead = []
        for ws in self.active_clients:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active_clients.discard(ws)

    # ------------------------------------------------------------------
    # Device Node Management (Daemons: Laptop, Mobile, IoT, Smart Home)
    # ------------------------------------------------------------------

    async def connect_device(self, node_id: str, websocket: WebSocket) -> None:
        """Register a hardware or smart home daemon node."""
        await websocket.accept()
        self.device_nodes[node_id] = websocket
        logger.info(f"[WS] Device node '{node_id}' connected. Total devices: {len(self.device_nodes)}")

        # Notify frontends that device is online
        await self.broadcast_to_clients({
            "type": "device_status_change",
            "node_id": node_id,
            "status": "online",
        })

    def disconnect_device(self, node_id: str) -> None:
        """Unregister a device node."""
        if node_id in self.device_nodes:
            del self.device_nodes[node_id]
            logger.info(f"[WS] Device node '{node_id}' disconnected. Remaining: {len(self.device_nodes)}")

    # ------------------------------------------------------------------
    # Remote Command Dispatch
    # ------------------------------------------------------------------

    async def dispatch_device_command(
        self, node_id: str, action: str, params: dict[str, Any] | None = None, timeout: float = 10.0
    ) -> dict[str, Any]:
        """
        Send a remote command to a connected device node and await the execution result.
        If node is not directly connected over WebSocket, returns a handled simulated fallback.
        """
        params = params or {}
        ws = self.device_nodes.get(node_id)

        # Broadcast execution start to frontend
        await self.broadcast_to_clients({
            "type": "agent_execution",
            "stage": "device_command",
            "node_id": node_id,
            "action": action,
            "params": params,
            "status": "dispatching",
        })

        if not ws:
            # If target is local host / laptop, execute directly using native OS APIs
            if node_id in {"laptop-primary", "host-local"} or "laptop" in node_id or "desktop" in node_id:
                logger.info(f"[WS] Executing hardware action '{action}' directly on host OS.")
                loop = asyncio.get_event_loop()
                res = await loop.run_in_executor(None, _execute_local_host_action, action, params)
            elif node_id in {"android-phone", "android-device"} or "android" in node_id or ("phone" in node_id and "ios" not in node_id):
                logger.info(f"[WS] Executing hardware action '{action}' directly on Android device.")
                from .android_service import android_bridge
                if action in {"lock", "lock_screen"}:
                    res = android_bridge.lock_screen()
                elif action in {"wake", "wake_screen"}:
                    res = android_bridge.wake_screen()
                elif action in {"volume", "set_volume"}:
                    pct = int(params.get("percent") or params.get("volume") or params.get("level") or 50)
                    res = android_bridge.set_volume(pct)
                elif action in {"open_app", "launch_app"}:
                    app = params.get("app_name") or params.get("app") or "youtube"
                    res = android_bridge.open_app(app)
                elif action in {"media", "play", "pause"}:
                    res = android_bridge.media_play_pause()
                elif action in {"screenshot", "capture"}:
                    from pathlib import Path
                    shot_dir = Path("backend/app/static/screenshots")
                    shot_dir.mkdir(parents=True, exist_ok=True)
                    shot_path = str(shot_dir / "phone_latest.png")
                    res = android_bridge.take_screenshot(shot_path)
            elif node_id in {"lg-qned-tv", "smart-tv"} or "tv" in node_id:
                logger.info(f"[WS] Executing hardware action '{action}' directly on LG QNED TV.")
                from .lg_tv_service import lg_tv
                if action in {"power", "power_toggle"}:
                    if lg_tv.is_available():
                        res = lg_tv.power_off()
                    else:
                        res = lg_tv.power_on()
                elif action in {"power_on", "wake_on_lan", "wake"}:
                    res = lg_tv.power_on()
                elif action in {"power_off", "turn_off"}:
                    res = lg_tv.power_off()
                elif action in {"volume", "set_volume"}:
                    vol = int(params.get("level") or params.get("volume") or params.get("percent") or 20)
                    res = lg_tv.set_volume(vol)
                elif action in {"volume_up", "vol_up"}:
                    res = lg_tv.volume_up()
                elif action in {"volume_down", "vol_down"}:
                    res = lg_tv.volume_down()
                elif action in {"mute", "unmute"}:
                    res = lg_tv.mute(params.get("muted", True))
                elif action in {"launch_app", "open_app"}:
                    app = params.get("app") or params.get("app_name") or "youtube"
                    res = lg_tv.launch_app(app)
                elif action in {"press_key", "key"}:
                    key = params.get("key") or "ENTER"
                    res = lg_tv.press_key(key)
                elif action in {"switch_input", "input"}:
                    inp = params.get("input") or "HDMI_1"
                    res = lg_tv.switch_input(inp)
                else:
                    res = {"status": "error", "message": f"Unknown TV action '{action}'."}
            elif node_id in {"ios-phone", "iphone"}:
                logger.info(f"[WS] Queuing hardware action '{action}' for iOS Apple Shortcuts.")
                from .ios_service import ios_bridge
                res = ios_bridge.queue_action(action, params)
            else:
                logger.info(f"[WS] Device '{node_id}' status updated with action '{action}'.")
                res = {
                    "node_id": node_id,
                    "action": action,
                    "status": "success",
                    "result": f"Action '{action}' executed for {node_id}.",
                }

            await self.broadcast_to_clients({
                "type": "agent_execution",
                "stage": "device_command",
                "node_id": node_id,
                "action": action,
                "status": res.get("status", "completed"),
                "result": res,
            })
            return res



        import uuid
        cmd_id = str(uuid.uuid4())
        loop = asyncio.get_event_loop()
        future: asyncio.Future = loop.create_future()
        self._pending_commands[cmd_id] = future

        payload = {
            "type": "command",
            "command_id": cmd_id,
            "action": action,
            "params": params,
        }

        try:
            await ws.send_json(payload)
            result = await asyncio.wait_for(future, timeout=timeout)
            await self.broadcast_to_clients({
                "type": "agent_execution",
                "stage": "device_command",
                "node_id": node_id,
                "action": action,
                "status": "completed",
                "result": result,
            })
            return result
        except asyncio.TimeoutError:
            logger.error(f"[WS] Command '{action}' to '{node_id}' timed out after {timeout}s.")
            err_res = {"node_id": node_id, "action": action, "status": "timeout", "error": "Device did not respond"}
            await self.broadcast_to_clients({
                "type": "agent_execution",
                "stage": "device_command",
                "node_id": node_id,
                "action": action,
                "status": "failed",
                "error": "Timeout",
            })
            return err_res
        finally:
            self._pending_commands.pop(cmd_id, None)

    def handle_device_response(self, command_id: str, result: dict[str, Any]) -> None:
        """Resolve a pending command future when device sends acknowledgement."""
        future = self._pending_commands.get(command_id)
        if future and not future.done():
            future.set_result(result)


# Global singleton instance
ws_hub = WebSocketManager()
