"""
lg_tv_service.py
----------------
Controls the LG QNED 65" TV over the local Wi-Fi network using the
WebOS SSAP (Simple Service Access Protocol) via pywebostv.

Capabilities:
  - Power On (Wake-on-LAN magic packet)
  - Power Off
  - Volume Up / Down / Set / Mute / Unmute
  - Change Input Source (HDMI-1, HDMI-2, …)
  - Launch App (YouTube, Netflix, Amazon Prime, Disney+, Spotify…)
  - Open URL in browser
  - Play / Pause / Stop media
  - Send remote-key press (arrow keys, OK, back, home, …)
  - Get TV state (power, volume, current app, inputs)

First-time setup:
  1. Ensure the TV and the machine running ARYA are on the same Wi-Fi.
  2. Set TV_IP in .env  (e.g., TV_IP=192.168.1.105).
  3. Optionally set TV_MAC for Wake-on-LAN (e.g., TV_MAC=AA:BB:CC:DD:EE:FF).
  4. The first time ARYA connects to the TV it will show a pairing prompt
     on screen — accept it once, and the client key is saved automatically
     to backend/tv_client_key.json for all future sessions.
"""

from __future__ import annotations

import json
import os
import socket
import struct
import threading
import time
from pathlib import Path
from typing import Optional

# --------------------------------------------------------------------------- #
# Config (read from .env dynamically)
# --------------------------------------------------------------------------- #
TV_CLIENT_KEY_PATH = Path(__file__).parent.parent / "tv_client_key.json"

_TV_LOCK = threading.Lock()
_client_cache = None          # cached WebOSClient instance
_client_connected_at: float = 0.0
_CLIENT_TTL = 60.0            # seconds before re-connecting


def _get_tv_ip() -> str:
    """Dynamically get TV IP from env or backend/.env."""
    ip = os.getenv("TV_IP", "").strip()
    if not ip:
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            from dotenv import load_dotenv
            load_dotenv(env_file)
            ip = os.getenv("TV_IP", "").strip()
    return ip


def _get_tv_mac() -> str:
    """Dynamically get TV MAC from env or backend/.env."""
    mac = os.getenv("TV_MAC", "").strip()
    if not mac:
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            from dotenv import load_dotenv
            load_dotenv(env_file)
            mac = os.getenv("TV_MAC", "").strip()
    return mac


# --------------------------------------------------------------------------- #
# Client key persistence helpers
# --------------------------------------------------------------------------- #

def _load_client_key() -> dict:
    if TV_CLIENT_KEY_PATH.exists():
        try:
            return json.loads(TV_CLIENT_KEY_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_client_key(store: dict) -> None:
    try:
        TV_CLIENT_KEY_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")
        print(f"[LG TV] Saved TV pairing client key to {TV_CLIENT_KEY_PATH.name}")
    except Exception as exc:
        print(f"[LG TV] Could not save client key: {exc}")


# --------------------------------------------------------------------------- #
# Wake-on-LAN
# --------------------------------------------------------------------------- #

def _wake_on_lan(mac: str) -> None:
    """Send a WoL magic packet to power on the TV."""
    mac_clean = mac.replace(":", "").replace("-", "").upper()
    if len(mac_clean) != 12:
        raise ValueError(f"Invalid MAC address: {mac}")
    magic = bytes.fromhex("FF" * 6 + mac_clean * 16)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        # Send to global broadcast
        try:
            sock.sendto(magic, ("255.255.255.255", 9))
        except Exception:
            pass
        # Send to specific subnet broadcast to ensure it routes over Wi-Fi adapter instead of Tailscale
        try:
            sock.sendto(magic, ("192.168.31.255", 9))
        except Exception:
            pass
    print(f"[LG TV] Wake-on-LAN packet sent to {mac}")


# --------------------------------------------------------------------------- #
# Connection helper
# --------------------------------------------------------------------------- #


def _is_tv_reachable(ip: str, port: int, timeout: float = 1.0) -> bool:
    import socket
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except (socket.timeout, OSError):
        return False

def _get_client():
    """Return a connected, registered WebOSClient (cached, thread-safe)."""
    global _client_cache, _client_connected_at

    tv_ip = _get_tv_ip()
    if not tv_ip:
        raise RuntimeError(
            "TV_IP is not set. Add TV_IP=<your-tv-ip> to backend/.env and restart ARYA."
        )

    with _TV_LOCK:
        now = time.time()
        if _client_cache is not None and (now - _client_connected_at) < _CLIENT_TTL:
            return _client_cache

        # Fast ping to prevent 21-second freeze when TV is completely off
        if not _is_tv_reachable(tv_ip, 3001, timeout=2.0) and not _is_tv_reachable(tv_ip, 3000, timeout=1.0):
            raise RuntimeError(f"LG TV at {tv_ip} is currently unreachable (Powered Off). Use the power on command first.")

        try:
            from pywebostv.connection import WebOSClient

            store = _load_client_key()

            # Connect with secure=True (modern LG webOS TVs like QNED require WSS on port 3001)
            client = None
            try:
                client = WebOSClient(tv_ip, secure=True)
                client.connect()
            except Exception as e_sec:
                try:
                    client = WebOSClient(tv_ip, secure=False)
                    client.connect()
                except Exception as e_unsec:
                    raise RuntimeError(f"Could not connect to LG TV at {tv_ip} (WSS: {e_sec}, WS: {e_unsec})")

            # Authenticate or pair
            has_saved_key = "client_key" in store
            timeout = 5 if has_saved_key else 45

            for status in client.register(store, timeout=timeout):
                from pywebostv.connection import WebOSClient as WC
                if status == WC.PROMPTED:
                    print(f"[LG TV] *** Please click 'Allow' on your LG TV screen at {tv_ip}! ***")
                elif status == WC.REGISTERED:
                    _save_client_key(store)
                    print("[LG TV] Registered successfully with LG TV. Key stored.")

            _client_cache = client
            _client_connected_at = time.time()
            return client

        except Exception as exc:
            _client_cache = None
            raise RuntimeError(f"Could not connect to LG TV at {tv_ip}: {exc}") from exc


def _reset_client() -> None:
    global _client_cache
    with _TV_LOCK:
        _client_cache = None


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

class LGTVBridge:
    """High-level async-safe bridge for LG WebOS TV control."""

    def is_paired(self) -> bool:
        """Check if we have a saved client key for the TV."""
        store = _load_client_key()
        return bool(store.get("client_key"))

    def is_available(self) -> bool:
        """Check if TV IP is configured and reachable."""
        ip = _get_tv_ip()
        if not ip:
            return False
        for port in (3001, 3000):
            try:
                with socket.create_connection((ip, port), timeout=0.5):
                    return True
            except OSError:
                pass
        return False

    # ---- Power ------------------------------------------------------------ #

    def power_off(self) -> dict:
        try:
            from pywebostv.controls import SystemControl
            ctrl = SystemControl(_get_client())
            ctrl.power_off()
            _reset_client()
            return {"ok": True, "action": "power_off"}
        except Exception as exc:
            _reset_client()
            return {"ok": False, "error": str(exc)}

    def power_on(self) -> dict:
        """Power on via Wake-on-LAN (WoL)."""
        mac = _get_tv_mac()
        if not mac:
            return {
                "ok": False,
                "error": "TV_MAC is not set. Add TV_MAC=<your-tv-mac-address> to backend/.env."
            }
        try:
            _wake_on_lan(mac)
            return {"ok": True, "action": "power_on", "note": "Wake-on-LAN packet sent — TV should wake up in ~3-5 seconds."}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # ---- Volume ------------------------------------------------------------ #

    def volume_up(self, steps: int = 1) -> dict:
        try:
            from pywebostv.controls import MediaControl
            ctrl = MediaControl(_get_client())
            for _ in range(max(1, steps)):
                ctrl.volume_up()
            return {"ok": True, "action": "volume_up", "steps": steps}
        except Exception as exc:
            _reset_client()
            return {"ok": False, "error": str(exc)}

    def volume_down(self, steps: int = 1) -> dict:
        try:
            from pywebostv.controls import MediaControl
            ctrl = MediaControl(_get_client())
            for _ in range(max(1, steps)):
                ctrl.volume_down()
            return {"ok": True, "action": "volume_down", "steps": steps}
        except Exception as exc:
            _reset_client()
            return {"ok": False, "error": str(exc)}

    def set_volume(self, level: int) -> dict:
        level = max(0, min(100, int(level)))
        try:
            from pywebostv.controls import MediaControl
            ctrl = MediaControl(_get_client())
            ctrl.set_volume(level)
            return {"ok": True, "action": "set_volume", "level": level}
        except Exception as exc:
            _reset_client()
            return {"ok": False, "error": str(exc)}

    def mute(self, muted: bool = True) -> dict:
        try:
            from pywebostv.controls import MediaControl
            ctrl = MediaControl(_get_client())
            ctrl.mute(muted)
            return {"ok": True, "action": "mute" if muted else "unmute"}
        except Exception as exc:
            _reset_client()
            return {"ok": False, "error": str(exc)}

    # ---- Media playback ---------------------------------------------------- #

    def play(self) -> dict:
        try:
            from pywebostv.controls import MediaControl
            ctrl = MediaControl(_get_client())
            ctrl.play()
            return {"ok": True, "action": "play"}
        except Exception as exc:
            _reset_client()
            return {"ok": False, "error": str(exc)}

    def pause(self) -> dict:
        try:
            from pywebostv.controls import MediaControl
            ctrl = MediaControl(_get_client())
            ctrl.pause()
            return {"ok": True, "action": "pause"}
        except Exception as exc:
            _reset_client()
            return {"ok": False, "error": str(exc)}

    def stop(self) -> dict:
        try:
            from pywebostv.controls import MediaControl
            ctrl = MediaControl(_get_client())
            ctrl.stop()
            return {"ok": True, "action": "stop"}
        except Exception as exc:
            _reset_client()
            return {"ok": False, "error": str(exc)}

    # ---- App Launcher ------------------------------------------------------ #

    # Well-known LG/WebOS App IDs
    _APP_IDS = {
        "youtube":       "youtube.leanback.v4",
        "netflix":       "netflix",
        "prime":         "amazon",
        "amazon":        "amazon",
        "hotstar":       "in.startv.hotstar",
        "jiohotstar":    "in.startv.hotstar",
        "disney":        "com.disney.disneyplus-prod",
        "spotify":       "spotify-beehive",
        "browser":       "com.webos.app.browser",
        "hdmi1":         "com.webos.app.hdmi1",
        "hdmi2":         "com.webos.app.hdmi2",
        "disney":        "com.disney.disneyplus-prod",
        "spotify":       "spotify-beehive",
        "browser":       "com.webos.app.browser",
        "hdmi1":         "com.webos.app.hdmi1",
        "hdmi2":         "com.webos.app.hdmi2",
        "hdmi3":         "com.webos.app.hdmi3",
        "hdmi4":         "com.webos.app.hdmi4",
        "livetv":        "com.webos.app.livetv",
        "settings":      "com.palm.app.settings",
        "music":         "com.webos.app.music",
        "photos":        "com.webos.app.photos",
        "screensaver":   "com.webos.app.screensaver",
    }

    def launch_app(self, app_name: str, url: Optional[str] = None) -> dict:
        """Launch an app by friendly name or WebOS App ID."""
        key = app_name.lower().strip()
        app_id = self._APP_IDS.get(key, app_name)   # fall-through: use as-is

        try:
            from pywebostv.controls import ApplicationControl, Application
            ctrl = ApplicationControl(_get_client())
            app_obj = Application({"id": app_id})

            if url and key in ("browser", "com.webos.app.browser"):
                # Open a specific URL in the browser
                ctrl.launch(app_obj, content_id=url)
            else:
                ctrl.launch(app_obj)

            return {"ok": True, "action": "launch_app", "app": app_id}
        except Exception as exc:
            _reset_client()
            return {"ok": False, "error": str(exc)}

    # ---- Input / Source switching ------------------------------------------ #

    def list_inputs(self) -> dict:
        try:
            from pywebostv.controls import InputControl
            ctrl = InputControl(_get_client())
            inputs = ctrl.list_inputs()
            return {"ok": True, "inputs": inputs}
        except Exception as exc:
            _reset_client()
            return {"ok": False, "error": str(exc)}

    def switch_input(self, input_id: str) -> dict:
        """Switch to an input source, e.g. 'HDMI_1', 'HDMI_2', 'AV_1'."""
        try:
            from pywebostv.controls import InputControl
            ctrl = InputControl(_get_client())
            ctrl.set_input(input_id)
            return {"ok": True, "action": "switch_input", "input": input_id}
        except Exception as exc:
            _reset_client()
            return {"ok": False, "error": str(exc)}

    # ---- Remote key presses ------------------------------------------------ #

    # WebOS key names
    _KEY_MAP = {
        "up": "UP", "down": "DOWN", "left": "LEFT", "right": "RIGHT",
        "ok": "ENTER", "enter": "ENTER", "back": "BACK", "home": "HOME",
        "menu": "MENU", "exit": "EXIT", "info": "INFO",
        "red": "RED", "green": "GREEN", "yellow": "YELLOW", "blue": "BLUE",
        "0": "0", "1": "1", "2": "2", "3": "3", "4": "4",
        "5": "5", "6": "6", "7": "7", "8": "8", "9": "9",
        "mute": "MUTE", "volumeup": "VOLUMEUP", "volumedown": "VOLUMEDOWN",
    }

    def press_key(self, key: str) -> dict:
        """Simulate a remote-control key press."""
        mapped = self._KEY_MAP.get(key.lower().replace(" ", ""), key.upper())
        try:
            from pywebostv.controls import InputControl
            ctrl = InputControl(_get_client())
            pointer = ctrl.connect_pointer_input()
            pointer.send_button(mapped)
            return {"ok": True, "action": "press_key", "key": mapped}
        except Exception as exc:
            _reset_client()
            return {"ok": False, "error": str(exc)}

    # ---- State ------------------------------------------------------------ #

    def get_state(self) -> dict:
        """Return current TV state: volume, foreground app, inputs."""
        tv_ip = _get_tv_ip()
        if not tv_ip:
            return {"ok": False, "error": "TV_IP not configured in backend/.env."}
        tv_mac = _get_tv_mac()
        state = {"ip": tv_ip, "mac": tv_mac}
        try:
            from pywebostv.controls import MediaControl, ApplicationControl

            client = _get_client()
            mc = MediaControl(client)
            ac = ApplicationControl(client)

            state["volume"] = mc.get_volume()
            state["foreground_app"] = ac.get_current()
            state["ok"] = True
        except Exception as exc:
            state["ok"] = False
            state["error"] = str(exc)
            _reset_client()
        return state


# Singleton
lg_tv = LGTVBridge()
