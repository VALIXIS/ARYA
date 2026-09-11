"""
smarthome_bridge.py
-------------------
Smart Home & IoT Daemon Bridge for Project ARYA.
Bridges smart appliances (Philips Hue/Tuya Lights, LG/Samsung/Android Smart TV, AC, Smart Plugs)
with ARYA's real-time WebSocket Hub. Supports Home Assistant integration or standalone IoT emulation.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [SMARTHOME] %(message)s")
logger = logging.getLogger("arya.smarthome")


class SmartHomeBridge:
    """Manages virtual and physical IoT devices connected to ARYA."""

    def __init__(self, server_url: str):
        self.server_url = server_url.rstrip("/")
        self.running = True

        # In-memory device registry and states
        self.devices = {
            "living-room-lights": {
                "name": "Living Room Smart Lights",
                "type": "light",
                "state": {"power": "on", "brightness": 80, "color": "#5B8CFF"},
            },
            "smart-tv-primary": {
                "name": "LG OLED 4K Smart TV",
                "type": "tv",
                "state": {"power": "standby", "volume": 22, "input": "HDMI 1", "app": "YouTube"},
            },
            "ac-bedroom": {
                "name": "Bedroom Climate AC",
                "type": "ac",
                "state": {"power": "on", "temperature": 23, "mode": "cool", "fan": "auto"},
            },
            "smart-plug-desk": {
                "name": "Office Desk Smart Plug",
                "type": "plug",
                "state": {"power": "on", "current_watts": 45},
            },
        }

    def execute_smarthome_action(self, node_id: str, action: str, params: dict) -> dict:
        """Handle incoming device control frames."""
        device = self.devices.get(node_id)
        if not device:
            # Try to match by partial name
            for k in self.devices:
                if k in node_id or node_id in k:
                    device = self.devices[k]
                    node_id = k
                    break

        if not device:
            return {"status": "error", "message": f"Device '{node_id}' not found in Smart Home registry."}

        state = device["state"]
        logger.info(f"Executing '{action}' on {device['name']} with params: {params}")

        # Lighting actions
        if action in {"turn_on", "power_on"}:
            state["power"] = "on"
            return {"status": "success", "message": f"{device['name']} is now ON.", "state": state}
        elif action in {"turn_off", "power_off"}:
            state["power"] = "off"
            return {"status": "success", "message": f"{device['name']} is now OFF.", "state": state}
        elif action in {"set_brightness", "dim", "brighten"}:
            val = params.get("value") or params.get("brightness") or 50
            try:
                state["brightness"] = int(val)
                state["power"] = "on"
            except ValueError:
                pass
            return {"status": "success", "message": f"{device['name']} brightness set to {state['brightness']}%.", "state": state}
        elif action in {"set_color", "color"}:
            c = params.get("value") or params.get("color") or "cyan"
            state["color"] = c
            return {"status": "success", "message": f"{device['name']} color changed to {c}.", "state": state}

        # TV actions
        elif action in {"set_tv_volume", "volume"}:
            vol = params.get("value") or params.get("volume") or 20
            state["volume"] = int(vol)
            return {"status": "success", "message": f"TV volume set to {state['volume']}.", "state": state}
        elif action in {"launch_app", "open_app"}:
            app = params.get("value") or params.get("app") or "YouTube"
            state["app"] = app
            state["power"] = "on"
            return {"status": "success", "message": f"Opened {app} on {device['name']}.", "state": state}

        # Climate actions
        elif action in {"set_climate", "set_temp", "set_temperature"}:
            val = params.get("value") or {}
            if isinstance(val, dict):
                temp = val.get("temperature", state.get("temperature", 22))
                mode = val.get("mode", state.get("mode", "cool"))
                state["temperature"] = temp
                state["mode"] = mode
            else:
                try:
                    state["temperature"] = int(val)
                except ValueError:
                    pass
            state["power"] = "on"
            return {
                "status": "success",
                "message": f"AC temperature set to {state['temperature']}C ({state.get('mode', 'cool')}).",
                "state": state,
            }

        return {"status": "success", "message": f"Updated {device['name']}: {action}", "state": state}

    async def connect_device_loop(self, node_id: str):
        """Persistent WebSocket loop for an individual smart device node."""
        import websockets
        ws_url = f"{self.server_url.replace('http://', 'ws://').replace('https://', 'wss://')}/ws/devices/{node_id}"

        while self.running:
            try:
                async with websockets.connect(ws_url) as ws:
                    logger.info(f"Connected IoT device '{node_id}' to ARYA hub.")
                    dev = self.devices[node_id]

                    # Register device
                    await ws.send(json.dumps({
                        "type": "heartbeat",
                        "node_id": node_id,
                        "name": dev["name"],
                        "device_type": dev["type"],
                        "state": dev["state"],
                    }))

                    while self.running:
                        msg_str = await ws.recv()
                        data = json.loads(msg_str)
                        if data.get("type") == "command":
                            cmd_id = data.get("command_id")
                            action = data.get("action")
                            params = data.get("params", {})
                            res = self.execute_smarthome_action(node_id, action, params)

                            await ws.send(json.dumps({
                                "type": "command_result",
                                "command_id": cmd_id,
                                "node_id": node_id,
                                "result": res,
                            }))
                            # Also broadcast new state
                            await ws.send(json.dumps({
                                "type": "state_update",
                                "node_id": node_id,
                                "state": dev["state"],
                            }))
            except Exception:
                await asyncio.sleep(4)

    async def run(self):
        """Run all smart home device loops concurrently."""
        tasks = [asyncio.create_task(self.connect_device_loop(node_id)) for node_id in self.devices]
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ARYA Smart Home & IoT Daemon Bridge")
    parser.add_argument("--server", default="http://localhost:8000", help="ARYA Backend server URL")
    args = parser.parse_args()

    bridge = SmartHomeBridge(server_url=args.server)
    try:
        asyncio.run(bridge.run())
    except KeyboardInterrupt:
        print("\n[SMARTHOME] Bridge stopped.")
