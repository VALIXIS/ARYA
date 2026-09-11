"""
settings_store.py
-----------------
Local settings persistence for ARYA Desktop.
"""

import json
import os
import sys
from pathlib import Path

DEFAULT_SETTINGS = {
    "launch_on_startup": False,
    "enable_notifications": False,
    "enable_daily_briefing": False,
    "last_daily_briefing_date": None,
    "last_task_reminder_date": None,
    "last_goal_reminder_date": None,
    # Voice settings
    "voice_enabled": True,
    "voice_auto_read": False,
    "voice_debug_logs": False,
}


def get_settings_path() -> Path:
    """Return the path to settings.json."""
    if sys.platform == "win32":
        base_dir = Path(os.environ.get("APPDATA", Path.home())) / "ARYA"
    else:
        base_dir = Path.home() / ".arya"

    return base_dir / "settings.json"


def load_settings() -> dict:
    """Load settings from disk, falling back to defaults."""
    settings_path = get_settings_path()
    if not settings_path.exists():
        return DEFAULT_SETTINGS.copy()

    try:
        with settings_path.open(encoding="utf-8") as settings_file:
            stored = json.load(settings_file)
    except (OSError, json.JSONDecodeError):
        return DEFAULT_SETTINGS.copy()

    return {**DEFAULT_SETTINGS, **stored}


def save_settings(settings: dict) -> None:
    """Persist settings to settings.json."""
    settings_path = get_settings_path()
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    with settings_path.open("w", encoding="utf-8") as settings_file:
        json.dump(settings, settings_file, indent=2)
