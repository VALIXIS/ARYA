"""
ios_service.py
--------------
Apple iOS / iPadOS Integration Service for Project ARYA.
Interfaces with Apple Shortcuts Webhooks, iOS Safari Web/PWA nodes,
and sends actionable payloads to iPhones/iPads.
"""

import logging
from typing import Any
from datetime import datetime, timezone

logger = logging.getLogger("arya.ios")

class IOSBridge:
    def __init__(self):
        self.pending_actions: list[dict[str, Any]] = []
        self.last_device_state: dict[str, Any] = {
            "battery": None,
            "charging": False,
            "dnd": False,
            "model": None,
            "last_seen": None,
        }


    def queue_action(self, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Queue an action to be fetched by the iPhone Apple Shortcut."""
        item = {
            "id": f"ios-cmd-{int(datetime.now().timestamp() * 1000)}",
            "action": action,
            "params": params or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.pending_actions.append(item)
        logger.info(f"[iOS] Queued action for iPhone: {item}")
        return {"success": True, "queued": item}

    def pop_pending_actions(self) -> list[dict[str, Any]]:
        """Fetch and clear queued actions for polling iOS Shortcuts."""
        actions = list(self.pending_actions)
        self.pending_actions.clear()
        return actions

    def record_telemetry(self, data: dict[str, Any]) -> dict[str, Any]:
        """Update telemetry sent from iPhone Shortcut webhook."""
        self.last_device_state.update(data)
        self.last_device_state["last_seen"] = datetime.now(timezone.utc).isoformat()
        return {"status": "ok", "state": self.last_device_state}

    def get_state(self) -> dict[str, Any]:
        return self.last_device_state

ios_bridge = IOSBridge()
