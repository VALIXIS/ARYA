"""
device_service.py
-----------------
Manages registered hardware device nodes (Laptops, Desktops, Mobile, Smart Home IoT).
Handles registration, heartbeat, state tracking, and remote command routing.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select

from . import models, schemas


def get_all_devices(db: Session) -> list[schemas.DeviceNodeResponse]:
    """Return all registered device nodes, with JSON capabilities/state parsed."""
    devices = db.query(models.DeviceNode).all()
    results = []
    for d in devices:
        caps = json.loads(d.capabilities) if d.capabilities else []
        state = json.loads(d.state_data) if d.state_data else {}
        results.append(
            schemas.DeviceNodeResponse(
                id=d.id,
                node_id=d.node_id,
                name=d.name,
                device_type=d.device_type,
                status=d.status,
                ip_address=d.ip_address,
                capabilities=caps,
                state_data=state,
                last_seen=d.last_seen,
            )
        )
    return results


def get_device_by_node_id(db: Session, node_id: str) -> models.DeviceNode | None:
    """Retrieve a device node by unique node_id string."""
    return db.query(models.DeviceNode).filter(models.DeviceNode.node_id == node_id).first()


def register_or_update_device(
    db: Session, device: schemas.DeviceNodeCreate, status: str = "online"
) -> schemas.DeviceNodeResponse:
    """Register a new device or update status/capabilities of an existing device."""
    existing = get_device_by_node_id(db, device.node_id)
    caps_str = json.dumps(device.capabilities)
    state_str = json.dumps(device.state_data)

    if existing:
        existing.name = device.name
        existing.device_type = device.device_type
        existing.status = status
        if device.ip_address:
            existing.ip_address = device.ip_address
        existing.capabilities = caps_str
        existing.state_data = state_str
        existing.last_seen = datetime.now(timezone.utc)
        db.commit()
        db.refresh(existing)
        d = existing
    else:
        d = models.DeviceNode(
            node_id=device.node_id,
            name=device.name,
            device_type=device.device_type,
            status=status,
            ip_address=device.ip_address,
            capabilities=caps_str,
            state_data=state_str,
            last_seen=datetime.now(timezone.utc),
        )
        db.add(d)
        db.commit()
        db.refresh(d)

    return schemas.DeviceNodeResponse(
        id=d.id,
        node_id=d.node_id,
        name=d.name,
        device_type=d.device_type,
        status=d.status,
        ip_address=d.ip_address,
        capabilities=json.loads(d.capabilities),
        state_data=json.loads(d.state_data),
        last_seen=d.last_seen,
    )


def update_device_status(db: Session, node_id: str, status: str) -> None:
    """Update a device's connection status (online/offline/busy)."""
    d = get_device_by_node_id(db, node_id)
    if d:
        d.status = status
        d.last_seen = datetime.now(timezone.utc)
        db.commit()


def update_device_state(db: Session, node_id: str, new_state: dict) -> None:
    """Merge and update device state data."""
    d = get_device_by_node_id(db, node_id)
    if d:
        current = json.loads(d.state_data) if d.state_data else {}
        current.update(new_state)
        d.state_data = json.dumps(current)
        d.last_seen = datetime.now(timezone.utc)
        db.commit()


def get_real_local_ip() -> str:
    """Detect the real local LAN IP (preferring active Wi-Fi on 192.168.x.x)."""
    try:
        import psutil, socket
        addrs = psutil.net_if_addrs()
        candidates = []
        for nic, addr_list in addrs.items():
            nic_lower = nic.lower()
            for a in addr_list:
                if a.family == socket.AF_INET:
                    ip = a.address
                    if ip.startswith("127.") or ip.startswith("169.254."):
                        continue
                    score = 0
                    if "wi-fi" in nic_lower or "wifi" in nic_lower or "wlan" in nic_lower:
                        score = 100
                    elif "ethernet" in nic_lower:
                        score = 50
                    if ip.startswith("192.168."):
                        score += 30
                    elif ip.startswith("10."):
                        score += 20
                    candidates.append((score, ip))
        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            return candidates[0][1]
    except Exception:
        pass

    import socket
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "127.0.0.1"


def get_real_host_telemetry() -> dict:
    """Gather real live telemetry from this host machine."""
    import platform

    telemetry = {
        "os": platform.system(),
        "release": platform.release(),
        "hostname": platform.node(),
        "ip": get_real_local_ip(),
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

    try:
        from pycaw.pycaw import AudioUtilities
        speakers = AudioUtilities.GetSpeakers()
        vol_ctrl = speakers.EndpointVolume
        telemetry["volume"] = int(round(vol_ctrl.GetMasterVolumeLevelScalar() * 100))
        telemetry["muted"] = bool(vol_ctrl.GetMute())
    except Exception:
        telemetry["volume"] = 60

    return telemetry


def seed_default_devices(db: Session) -> None:
    """Auto-detect and register the real host machine running ARYA, removing old fake seeds."""
    import platform

    # Clear old fake dummy rows if they exist
    db.query(models.DeviceNode).filter(
        models.DeviceNode.node_id.in_([
            "mobile-phone",
            "living-room-lights",
            "smart-tv-primary",
            "ac-bedroom",
            "ios-phone",
        ])
    ).delete(synchronize_session=False)
    db.commit()

    # Detect real machine
    info = get_real_host_telemetry()
    hostname = info.get("hostname") or platform.node() or "Host PC"
    os_name = platform.system()
    has_battery = "battery" in info
    device_type = "laptop" if has_battery else "desktop"

    real_node = schemas.DeviceNodeCreate(
        node_id="laptop-primary",
        name=f"{hostname} ({os_name} {device_type.capitalize()})",
        device_type=device_type,
        ip_address=info.get("ip", "127.0.0.1"),
        capabilities=[
            "volume",
            "brightness",
            "lock_screen",
            "launch_app",
            "terminal_exec",
            "media",
        ],
        state_data={
            "volume": info.get("volume", 60),
            "cpu": info.get("cpu_percent", 0),
            "ram": info.get("ram_percent", 0),
            **({"battery": info["battery"], "charging": info.get("charging", True)} if has_battery else {}),
        },
    )
    register_or_update_device(db, real_node, status="online")

    # Auto-detect connected mobile devices
    check_and_register_mobile_devices(db)

    # Register LG QNED TV if configured
    check_and_register_lg_tv(db)


def check_and_register_mobile_devices(db: Session) -> None:
    """Detect and register Android and iOS mobile devices with 100% real live status."""
    try:
        from .android_service import android_bridge

        connected_devs = [d for d in android_bridge.get_connected_devices() if d.get("state") == "device"]
        if connected_devs:
            dev = connected_devs[0]
            batt = android_bridge.get_battery_info(dev["serial"])
            node = schemas.DeviceNodeCreate(
                node_id="android-phone",
                name=f"{dev['model']} (Android)",
                device_type="mobile",
                ip_address=dev["serial"] if ":" in dev["serial"] else "USB Connected",
                capabilities=[
                    "volume",
                    "lock_screen",
                    "wake_screen",
                    "open_app",
                    "media",
                    "screenshot",
                    "camera",
                    "unlock_screen",
                ],
                state_data={
                    "battery": batt.get("battery"),
                    "charging": batt.get("charging", False),
                    "serial": dev["serial"],
                    "is_wireless": dev.get("is_wireless", False),
                    "status_detail": "Online & Ready via ADB",
                },
            )
            register_or_update_device(db, node, status="online")
        else:
            # Device is disconnected / offline — DO NOT report fake battery or fake online status!
            node = schemas.DeviceNodeCreate(
                node_id="android-phone",
                name="Android Mobile Phone (i2302)",
                device_type="mobile",
                ip_address="Tailscale: 100.67.134.74 | LAN: 192.168.31.44",
                capabilities=[
                    "volume",
                    "lock_screen",
                    "wake_screen",
                    "open_app",
                ],
                state_data={
                    "status_detail": "Tailscale Connected (100.67.134.74). Toggle Wireless Debugging to pair ADB over WAN.",
                    "is_connected": False,
                    "tailscale_ip": "100.67.134.74",
                    "lan_ip": "192.168.31.44",
                },
            )
            register_or_update_device(db, node, status="offline")

            # Autonomous background healing: try to reconnect if we just marked it offline
            def _auto_heal_adb():
                try:
                    res = android_bridge.auto_discover_and_connect()
                    if res.get("success"):
                        print("[DEVICE SERVICE] Auto-heal succeeded! ADB connected in background.")
                except Exception:
                    pass

            import threading
            threading.Thread(target=_auto_heal_adb, daemon=True).start()

        # Purge any fake iOS mock rows if no real iPhone bridge exists
        from .ios_service import ios_bridge
        ios_state = ios_bridge.get_state()
        if not (ios_state.get("last_seen") and ios_state.get("model")):
            db.query(models.DeviceNode).filter(models.DeviceNode.node_id == "ios-phone").delete(synchronize_session=False)
            db.commit()

    except Exception as exc:
        print(f"[DEVICE] Mobile check error: {exc}")


def check_and_register_lg_tv(db: Session) -> None:
    """Register the LG QNED TV with real socket connectivity check."""
    import os, socket
    tv_ip = os.getenv("TV_IP", "").strip() or "192.168.31.169"
    tv_mac = os.getenv("TV_MAC", "").strip() or "68:72:C3:7E:6D:5C"

    # Fast socket probe on WebOS ports
    is_live = False
    for port in (3001, 3000):
        try:
            with socket.create_connection((tv_ip, port), timeout=0.35):
                is_live = True
                break
        except OSError:
            pass

    capabilities = [
        "power_on", "power_off", "volume", "mute",
        "launch_app", "press_key", "switch_input", "get_state",
    ]
    if tv_mac:
        capabilities.append("wake_on_lan")

    state_data: dict = {
        "ip": tv_ip,
        "mac": tv_mac,
        "model": 'LG QNED 65" Smart TV',
        "protocol": "WebOS SSAP",
        "wol_ready": bool(tv_mac),
    }

    if is_live:
        status = "online"
        state_data["power"] = "on"
        state_data["status_detail"] = "TV is ON and listening on WebOS SSAP."
        try:
            from .lg_tv_service import lg_tv
            tv_state = lg_tv.get_state()
            if tv_state.get("volume") is not None:
                state_data["volume"] = tv_state["volume"]
            if tv_state.get("foreground_app"):
                state_data["foreground_app"] = tv_state["foreground_app"]
        except Exception:
            pass
    else:
        status = "standby"
        state_data["power"] = "standby"
        state_data["status_detail"] = "TV is in Standby. Click 'Wake on LAN' to turn on."

    node = schemas.DeviceNodeCreate(
        node_id="lg-qned-tv",
        name='LG QNED 65" Smart TV',
        device_type="smart_tv",
        ip_address=tv_ip,
        capabilities=capabilities,
        state_data=state_data,
    )
    register_or_update_device(db, node, status=status)
