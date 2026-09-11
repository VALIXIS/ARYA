"""
android_service.py
------------------
Autonomous Android Device Bridge for Project ARYA.
Interfaces with local ADB (Android Debug Bridge) to auto-detect and control
Android smartphones/tablets via USB or Wireless Wi-Fi ADB.

Supported Capabilities:
- Auto-discovery of connected devices (USB & Wi-Fi)
- Wireless ADB connection (adb connect <ip>:<port>)
- App launching (YouTube, WhatsApp, Spotify, Settings, Camera, Maps, Chrome, etc.)
- Screen Lock / Screen Wake
- Volume & Media playback control
- Real-time screenshot capture
- Intent dispatch (URLs, SMS, phone calls)
- Shell keyevents & text input
"""

import os
import re
import shutil
import subprocess
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("arya.android")

def _find_adb_path() -> str:
    path = shutil.which("adb")
    if path:
        return path
    candidates = [
        Path.home() / "AppData" / "Local" / "Android" / "Sdk" / "platform-tools" / "adb.exe",
        Path("C:/Android/platform-tools/adb.exe"),
        Path("C:/Program Files/Android/platform-tools/adb.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return "adb"

ADB_PATH = _find_adb_path()

KNOWN_PACKAGES: dict[str, str] = {
    "youtube": "com.google.android.youtube",
    "whatsapp": "com.whatsapp",
    "spotify": "com.spotify.music",
    "chrome": "com.android.chrome",
    "maps": "com.google.android.apps.maps",
    "google maps": "com.google.android.apps.maps",
    "camera": "com.android.camera",
    "settings": "com.android.settings",
    "setting": "com.android.settings",
    "display": "com.android.settings",
    "gmail": "com.google.android.gm",
    "telegram": "org.telegram.messenger",
    "instagram": "com.instagram.android",
    "netflix": "com.netflix.mediaclient",
    "photos": "com.google.android.apps.photos",
    "clock": "com.google.android.deskclock",
    "calculator": "com.google.android.calculator",
    "phone": "com.google.android.dialer",
    "dialer": "com.google.android.dialer",
}

def _run_adb(args: list[str], timeout: float = 10.0, retry_on_offline: bool = True) -> tuple[int, str, str]:
    cmd = [ADB_PATH] + args
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        out = proc.stdout.strip()
        err = proc.stderr.strip()
        combined = (out + " " + err).lower()

        # Handle offline or lost connection with auto-reconnect
        if retry_on_offline and ("device offline" in combined or "device not found" in combined):
            if args and args[0] not in {"devices", "connect", "pair", "mdns", "kill-server", "start-server"}:
                logger.info("[ADB Auto-Heal] Device offline or not found. Attempting autonomous mDNS reconnect...")
                _heal_res = AndroidBridge.auto_discover_and_connect()
                if _heal_res.get("success"):
                    return _run_adb(args, timeout=timeout, retry_on_offline=False)

        if "no devices" in combined:
            err = (
                "No Android phone detected. If you recently changed Wi-Fi, "
                "please check Developer Options > Wireless Debugging (a new port may have been generated), "
                "or connect via USB cable once with USB Debugging enabled."
            )
        elif "device offline" in combined:
            err = (
                "Android phone is currently in an offline state (Wi-Fi was reset or reconnecting). "
                "Please toggle Wireless Debugging OFF and ON in Developer Options, or connect via USB cable."
            )
        return proc.returncode, out, err
    except subprocess.TimeoutExpired:
        logger.error(f"[ADB] Command timed out: {' '.join(cmd)}")
        return -1, "", "Timeout: phone did not respond in time"
    except Exception as exc:
        logger.error(f"[ADB] Execution error: {exc}")
        return -1, "", str(exc)

class AndroidBridge:
    @staticmethod
    def is_available() -> bool:
        code, out, _ = _run_adb(["version"], retry_on_offline=False)
        return code == 0

    @staticmethod
    def get_connected_devices() -> list[dict[str, Any]]:
        code, out, _ = _run_adb(["devices", "-l"], retry_on_offline=False)
        if code != 0 or not out:
            return []
        devices = []
        for line in out.splitlines()[1:]:
            line = line.strip()
            if not line or line.startswith("*"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                serial = parts[0]
                state = parts[1]
                model = "Android Device"
                for item in parts[2:]:
                    if item.startswith("model:"):
                        model = item.split(":", 1)[1].replace("_", " ")
                    elif item.startswith("device:"):
                        if model == "Android Device":
                            model = item.split(":", 1)[1]
                devices.append({
                    "serial": serial,
                    "state": state,
                    "model": model,
                    "is_wireless": ":" in serial,
                })
        return devices

    @staticmethod
    def discover_mdns_services() -> list[dict[str, Any]]:
        """
        Query ADB mDNS services to discover wireless debugging and pairing endpoints.
        Returns list of dicts: [{'service': '_adb-tls-connect._tcp', 'ip': '192.168.31.44', 'port': 41501}, ...]
        """
        code, out, _ = _run_adb(["mdns", "services"], retry_on_offline=False)
        services = []
        for line in out.splitlines():
            parts = line.strip().split()
            if len(parts) >= 3:
                svc_type = parts[1]
                addr = parts[2]
                if ":" in addr:
                    ip, port_str = addr.split(":", 1)
                    try:
                        services.append({
                            "service": svc_type,
                            "ip": ip,
                            "port": int(port_str),
                            "name": parts[0],
                        })
                    except ValueError:
                        pass
        return services

    @classmethod
    def auto_discover_and_connect(cls) -> dict[str, Any]:
        """
        Autonomous self-healing connection routine:
        1. Check if device already online.
        2. Clean up any stale offline device states.
        3. Query mDNS services for active _adb-tls-connect endpoints.
        4. Attempt connection across Tailscale and LAN IPs and candidate ports.
        """
        # 1. Check if already online
        online_devices = [d for d in cls.get_connected_devices() if d.get("state") == "device"]
        if online_devices:
            return {"success": True, "message": f"Already connected to {online_devices[0]['model']}.", "device": online_devices[0]}

        # 2. Flush offline states
        offline_devices = [d for d in cls.get_connected_devices() if d.get("state") == "offline"]
        if offline_devices:
            for d in offline_devices:
                _run_adb(["disconnect", d["serial"]], retry_on_offline=False)
            _run_adb(["reconnect"], retry_on_offline=False)

        # 3. Discover active port via mDNS
        services = cls.discover_mdns_services()
        connect_svcs = [s for s in services if "_adb-tls-connect" in s["service"]]

        if connect_svcs:
            best = connect_svcs[0]
            target_ip = best["ip"]
            target_port = best["port"]
            logger.info(f"[ADB Auto-Heal] Discovered phone via mDNS at {target_ip}:{target_port}. Attempting connection...")
            res = cls.connect_wireless(target_ip, target_port)
            if res.get("success"):
                return {"success": True, "message": f"Auto-discovered and connected to phone at {target_ip}:{target_port}!"}

        # 4. Fallback across candidate IPs (Tailscale & LAN) and common Wireless Debugging ports
        # Re-ordered to prioritize 5555 (our forced TCP/IP port) to make auto-healing instantaneous!
        candidate_ips = ["100.67.134.74", "192.168.31.44"]
        candidate_ports = [5555, 41501, 33257, 37000, 38000, 39000, 40000, 41000, 42000, 43000, 44000, 45000]

        for ip in candidate_ips:
            for p in candidate_ports:
                res = cls.connect_wireless(ip, p)
                if res.get("success"):
                    return {"success": True, "message": f"Connected to phone at {ip}:{p}!"}

        if connect_svcs:
            s = connect_svcs[0]
            return {
                "success": False,
                "message": (
                    f"Discovered phone on Wi-Fi at {s['ip']}:{s['port']}. "
                    "Initial pairing required: tap 'Pair device with pairing code' "
                    "in Developer Options and say: 'pair phone with code <6-digit-code>', "
                    "or connect via USB cable once with USB debugging enabled."
                ),
            }

        return {
            "success": False,
            "message": (
                "No phone discovered on Wi-Fi or Tailscale. "
                "Please verify Wireless Debugging is toggled ON in Developer Options, "
                "or connect via USB cable."
            ),
        }

    @classmethod
    def pair_wireless(cls, ip: str, port: int, pairing_code: str) -> dict[str, Any]:
        # If user didn't specify pairing port or passed default/0, auto-discover pairing port from mDNS!
        if not port or port in (5555, 33257, 0):
            services = cls.discover_mdns_services()
            pairing_svcs = [s for s in services if "_adb-tls-pairing" in s["service"]]
            if pairing_svcs:
                port = pairing_svcs[0]["port"]
                ip = pairing_svcs[0]["ip"]
                print(f"[ADB Pair] Auto-discovered pairing port from mDNS: {ip}:{port}")

        target = f"{ip}:{port}"
        code, out, err = _run_adb(["pair", target, str(pairing_code).strip()], retry_on_offline=False)
        output_combined = (out + " " + err).strip()
        success = "successfully paired" in output_combined.lower() or code == 0

        if success:
            # Auto-connect immediately after pairing
            cls.auto_discover_and_connect()
            return {
                "success": True,
                "message": f"Successfully paired with phone at {target} and connected!",
                "target": target,
            }

        return {
            "success": False,
            "message": f"Pairing failed on {target}: {output_combined}",
            "target": target,
        }

    @classmethod
    def connect_wireless(cls, ip: str, port: int = 0) -> dict[str, Any]:
        # If port is 0 or default, try mDNS discovery first, then scan candidate ports for this IP
        if not port or port == 0:
            services = cls.discover_mdns_services()
            connect_svcs = [s for s in services if "_adb-tls-connect" in s["service"]]
            if connect_svcs:
                ip = connect_svcs[0]["ip"]
                port = connect_svcs[0]["port"]
            else:
                candidate_ports = [41501, 33257, 5555, 37000, 38000, 39000, 40000, 41000, 42000, 43000, 44000, 45000]
                for p in candidate_ports:
                    res = cls.connect_wireless(ip, p)
                    if res.get("success"):
                        return res
                return {"success": False, "message": f"Could not auto-connect to {ip}. Please specify exact port."}

        target = f"{ip}:{port}" if port else ip
        code, out, err = _run_adb(["connect", target], retry_on_offline=False)
        combined = (out + " " + err).strip()
        success = "connected to" in combined.lower() and "failed" not in combined.lower()
        if not success:
            msg = (
                f"Could not connect to {target} ({combined}). "
                "For Android 11+ Wireless Debugging, tap 'Pair device with pairing code' "
                "in Developer Options and say: 'pair phone with code <6-digit>', "
                "or connect via USB cable once with USB Debugging enabled."
            )
        else:
            msg = f"Connected to Android phone at {target}."
        return {"success": success, "message": msg, "target": target}

    @staticmethod
    def disconnect_wireless(ip: str, port: int = 5555) -> dict[str, Any]:
        target = f"{ip}:{port}"
        code, out, _ = _run_adb(["disconnect", target], retry_on_offline=False)
        return {"success": code == 0, "message": out}

    DEFAULT_PIN: str = "9603"

    @staticmethod
    def unlock_screen(pin: str = "9603", serial: str | None = None) -> dict[str, Any]:
        """Wake phone and unlock screen using user's secure PIN."""
        args = ["-s", serial] if serial else []
        import time
        # 1. Wake screen
        _run_adb(args + ["shell", "input", "keyevent", "224"])
        time.sleep(0.3)
        # 2. Swipe up to reveal keypad / dismiss lockscreen
        _run_adb(args + ["shell", "input", "swipe", "540", "1800", "540", "500", "200"])
        _run_adb(args + ["shell", "input", "keyevent", "82"])
        time.sleep(0.3)
        # 3. Enter PIN
        _run_adb(args + ["shell", "input", "text", pin])
        time.sleep(0.2)
        # 4. Press Enter
        code, out, err = _run_adb(args + ["shell", "input", "keyevent", "66"])
        return {"success": code == 0, "message": f"Phone unlocked successfully with PIN {pin}."}

    @classmethod
    def ensure_unlocked(cls, pin: str = "9603", serial: str | None = None) -> None:
        """Helper to ensure phone screen is turned on and unlocked before executing tasks."""
        try:
            cls.unlock_screen(pin=pin, serial=serial)
        except Exception as exc:
            logger.warning(f"[ADB] Failed to unlock screen: {exc}")

    @classmethod
    def play_youtube_video(cls, query: str, serial: str | None = None) -> dict[str, Any]:
        """Search YouTube and play the top video directly on the Android phone."""
        cls.ensure_unlocked(cls.DEFAULT_PIN, serial=serial)
        from .tools.browser_tools import _scrape_first_youtube_video
        video_url = _scrape_first_youtube_video(query)
        if not video_url:
            video_url = "https://www.youtube.com/results?search_query=" + query.replace(" ", "+")
        args = ["-s", serial] if serial else []
        code, out, err = _run_adb(args + ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", video_url])
        return {
            "success": code == 0,
            "message": f"Playing '{query}' on phone YouTube." if code == 0 else f"Failed to play on phone: {err}",
            "url": video_url,
        }

    @classmethod
    def open_whatsapp(cls, contact: str | None = None, message: str | None = None, serial: str | None = None) -> dict[str, Any]:
        """Launch WhatsApp on phone and optionally open chat with specified contact. Uses instant Deep Links for numbers."""
        cls.ensure_unlocked(cls.DEFAULT_PIN, serial=serial)
        args = ["-s", serial] if serial else []
        import time

        # ULTRA-FAST PATH: If contact is a phone number, use the WhatsApp API Deep Link
        # This completely bypasses the UI search and instantly opens the chat with pre-filled text!
        if contact and re.match(r"^\+?\d{10,}$", contact.replace(" ", "")):
            num = contact.replace(" ", "")
            # Assume India (+91) if no country code provided
            if len(num) == 10:
                num = "91" + num
            elif num.startswith("+"):
                num = num[1:]
            
            import urllib.parse
            safe_msg = urllib.parse.quote(message) if message else ""
            url = f"https://api.whatsapp.com/send?phone={num}&text={safe_msg}"
            
            _run_adb(args + ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", f"'{url}'", "-p", "com.whatsapp"])
            time.sleep(1.0)
            
            if message:
                # Press Send button (Enter)
                _run_adb(args + ["shell", "input", "keyevent", "66"])
                _run_adb(args + ["shell", "input", "keyevent", "22"]) # Right to send button just in case
                _run_adb(args + ["shell", "input", "keyevent", "66"])
            
            res_msg = f"Instantly opened WhatsApp chat with '{num}' via Deep Link."
            return {"success": True, "message": res_msg}

        # LEGACY PATH: UI Search for Contact Names (e.g. 'Adithya VVIT')
        _run_adb(args + ["shell", "am", "start", "-n", "com.whatsapp/.Main"])
        time.sleep(0.6)

        if contact:
            # Trigger search icon and input contact name (space escaped for adb)
            contact_fmt = contact.replace(" ", "%s")
            _run_adb(args + ["shell", "input", "keyevent", "84"]) # Search
            time.sleep(0.3)
            _run_adb(args + ["shell", "input", "text", contact_fmt])
            time.sleep(0.4)
            _run_adb(args + ["shell", "input", "keyevent", "20"]) # Down
            time.sleep(0.2)
            _run_adb(args + ["shell", "input", "keyevent", "66"]) # Enter
            time.sleep(0.5)

        if message:
            message_fmt = message.replace(" ", "%s")
            _run_adb(args + ["shell", "input", "text", message_fmt])
            time.sleep(0.3)
            _run_adb(args + ["shell", "input", "keyevent", "66"]) # Send message

        res_msg = f"Opened WhatsApp on phone and sent message to '{contact}'." if (contact and message) else (f"Opened WhatsApp on phone for chat with '{contact}'." if contact else "Opened WhatsApp on phone.")
        return {
            "success": True,
            "message": res_msg
        }

    @staticmethod
    def lock_screen(serial: str | None = None) -> dict[str, Any]:
        args = ["-s", serial] if serial else []
        code, _, err = _run_adb(args + ["shell", "input", "keyevent", "26"])
        return {"success": code == 0, "message": "Phone locked." if code == 0 else err}

    @staticmethod
    def wake_screen(serial: str | None = None) -> dict[str, Any]:
        args = ["-s", serial] if serial else []
        code, _, err = _run_adb(args + ["shell", "input", "keyevent", "224"])
        return {"success": code == 0, "message": "Phone screen awakened." if code == 0 else err}

    @staticmethod
    def set_volume(percent: int, serial: str | None = None) -> dict[str, Any]:
        val = max(0, min(15, int(percent * 15 / 100)))
        args = ["-s", serial] if serial else []
        code, out, err = _run_adb(args + ["shell", "cmd", "media_session", "volume", "--show", "--set", str(val)])
        if code != 0:
            code, out, err = _run_adb(args + ["shell", "media", "volume", "--stream", "3", "--set", str(val)])
        return {"success": code == 0, "message": f"Phone volume set to {percent}% (level {val}/15)."}

    @staticmethod
    def media_play_pause(serial: str | None = None) -> dict[str, Any]:
        args = ["-s", serial] if serial else []
        code, _, _ = _run_adb(args + ["shell", "input", "keyevent", "85"])
        return {"success": code == 0, "message": "Toggled media playback on phone."}

    @classmethod
    def open_app(cls, app_name: str, search_query: str | None = None, serial: str | None = None) -> dict[str, Any]:
        cls.ensure_unlocked(cls.DEFAULT_PIN, serial=serial)
        name_clean = app_name.lower().strip()
        args = ["-s", serial] if serial else []
        import time

        # Special direct shortcut for Display settings
        if name_clean in {"settings", "setting"} and search_query and "display" in search_query.lower():
            code_d, _, _ = _run_adb(args + ["shell", "am", "start", "-a", "android.settings.DISPLAY_SETTINGS"])
            if code_d == 0:
                return {"success": True, "message": "Opened Display Settings on phone."}

        package = KNOWN_PACKAGES.get(name_clean, name_clean)
        code, out, err = _run_adb(
            args + ["shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"]
        )
        if "Events injected: 1" not in out:
            code2, _, _ = _run_adb(args + ["shell", "am", "start", "-a", "android.intent.action.MAIN", "-p", package])
            if code2 != 0 and name_clean in {"settings", "setting"}:
                _run_adb(args + ["shell", "am", "start", "-a", "android.settings.SETTINGS"])

        if search_query:
            time.sleep(0.8)
            # Try KEYCODE_SEARCH (84) or tapping search
            _run_adb(args + ["shell", "input", "keyevent", "84"])
            time.sleep(0.3)
            safe_query = search_query.replace(" ", "%s")
            _run_adb(args + ["shell", "input", "text", safe_query])
            time.sleep(0.3)
            _run_adb(args + ["shell", "input", "keyevent", "66"])  # Enter
            return {"success": True, "message": f"Opened '{app_name}' on phone and searched for '{search_query}'."}

        return {"success": True, "message": f"Launched '{app_name}' on phone."}

    @staticmethod
    def open_url(url: str, serial: str | None = None) -> dict[str, Any]:
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        args = ["-s", serial] if serial else []
        code, _, err = _run_adb(args + ["shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", url])
        return {"success": code == 0, "message": f"Opened {url} on phone." if code == 0 else err}

    @staticmethod
    def take_screenshot(output_path: str, serial: str | None = None) -> dict[str, Any]:
        args = ["-s", serial] if serial else []
        cmd = [ADB_PATH] + args + ["exec-out", "screencap", "-p"]
        try:
            with open(output_path, "wb") as f:
                proc = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, timeout=8.0)
            if proc.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                return {"success": True, "path": output_path, "message": "Phone screenshot captured."}
            return {"success": False, "message": "Screenshot capture failed."}
        except Exception as exc:
            return {"success": False, "message": str(exc)}

    @staticmethod
    def get_battery_info(serial: str | None = None) -> dict[str, Any]:
        args = ["-s", serial] if serial else []
        code, out, _ = _run_adb(args + ["shell", "dumpsys", "battery"])
        if code != 0 or not out:
            return {}
        info = {}
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("level:"):
                info["battery"] = int(line.split(":", 1)[1].strip())
            elif line.startswith("status:"):
                st = int(line.split(":", 1)[1].strip())
                info["charging"] = st in {2, 5}
        return info

    @classmethod
    def initiate_call(cls, number: str, serial: str | None = None) -> dict[str, Any]:
        """Directly initiate a cellular phone call using Android Intents."""
        cls.ensure_unlocked(cls.DEFAULT_PIN, serial=serial)
        args = ["-s", serial] if serial else []
        # Use ACTION_CALL to bypass dialer and call directly
        safe_num = number.replace(" ", "")
        code, out, err = _run_adb(args + ["shell", "am", "start", "-a", "android.intent.action.CALL", "-d", f"tel:{safe_num}"])
        if code == 0:
            return {"success": True, "message": f"Initiated phone call to {number}."}
        return {"success": False, "message": f"Failed to initiate call: {err}"}

android_bridge = AndroidBridge()
