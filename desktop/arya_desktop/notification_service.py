"""
notification_service.py
-----------------------
Windows notifications for ARYA Desktop.
"""

import sys
from datetime import datetime

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QSystemTrayIcon

from arya_desktop import settings_store
from arya_desktop.api_client import ApiClient

MORNING_HOUR = 8
MAX_ITEMS = 5
MAX_NEWS_HEADLINES = 2
MAX_MESSAGE_CHARS = 900


def is_windows() -> bool:
    """Return True when running on Windows."""
    return sys.platform == "win32"


def _pending_tasks(tasks: list[dict]) -> list[dict]:
    """Return tasks that are not completed."""
    return [task for task in tasks if task.get("status", "").lower() != "completed"]


def _active_goals(goals: list[dict]) -> list[dict]:
    """Return goals that are not completed."""
    return [goal for goal in goals if goal.get("status", "").lower() != "completed"]


def _truncate_message(message: str) -> str:
    """Keep notification text within a safe display length."""
    message = message.strip()
    if len(message) <= MAX_MESSAGE_CHARS:
        return message
    return message[: MAX_MESSAGE_CHARS - 3].rstrip() + "..."


def _format_item_list(title: str, items: list[dict], empty_label: str) -> str:
    """Format a titled bullet list for notifications."""
    if not items:
        return f"{title}:\n{empty_label}"

    lines = "\n".join(f"- {item.get('title', 'Untitled')}" for item in items[:MAX_ITEMS])
    if len(items) > MAX_ITEMS:
        lines += f"\n- +{len(items) - MAX_ITEMS} more"
    return f"{title}:\n{lines}"


def _format_news_section(title: str, headlines: list[dict], limit: int = MAX_NEWS_HEADLINES) -> str | None:
    """Format a news section for notifications."""
    if not headlines:
        return None

    lines = "\n".join(f"* {item.get('title', 'Untitled')}" for item in headlines[:limit])
    return f"{title}:\n{lines}"


def _format_profile_highlights(profile_text: str) -> str:
    """Extract a compact profile summary for notifications."""
    if not profile_text or profile_text.strip().lower().startswith("no profile"):
        return "Profile Highlights:\n(none)"

    lines = [line.strip() for line in profile_text.splitlines() if line.strip()]
    highlights = lines[:6]
    if not highlights:
        return "Profile Highlights:\n(none)"

    return "Profile Highlights:\n" + "\n".join(f"- {line.lstrip('- ')}" for line in highlights)


class NotificationService:
    """Send Windows tray notifications for ARYA reminders."""

    def __init__(self, tray_icon: QSystemTrayIcon | None = None):
        self.tray_icon = tray_icon

    def notifications_enabled(self) -> bool:
        """Return True when notifications are enabled and supported."""
        if not is_windows() or self.tray_icon is None:
            return False
        settings = settings_store.load_settings()
        return bool(settings.get("enable_notifications", False))

    def daily_briefing_enabled(self) -> bool:
        """Return True when daily briefing notifications should be sent."""
        settings = settings_store.load_settings()
        return self.notifications_enabled() and bool(
            settings.get("enable_daily_briefing", False)
        )

    def _show(self, title: str, message: str) -> None:
        """Display a Windows notification when enabled."""
        if not self.notifications_enabled() or self.tray_icon is None:
            return

        self.tray_icon.showMessage(
            title,
            _truncate_message(message),
            QSystemTrayIcon.Information,
            10000,
        )

    def build_daily_briefing(
        self,
        goals: list[dict],
        tasks: list[dict],
        profile_text: str,
        news_data: dict | None = None,
    ) -> str:
        """Build the daily briefing notification body."""
        sections = [
            _format_item_list("Goals", _active_goals(goals), "(none)"),
            _format_item_list("Pending Tasks", _pending_tasks(tasks), "(none)"),
            _format_profile_highlights(profile_text),
        ]

        if news_data:
            ai_section = _format_news_section(
                "AI News",
                news_data.get("ai_news", []),
            )
            if ai_section:
                sections.append(ai_section)

            tech_section = _format_news_section(
                "Technology News",
                news_data.get("technology_news", []),
            )
            if tech_section:
                sections.append(tech_section)

        return "\n\n".join(sections)

    def show_task_reminder(self, tasks: list[dict]) -> None:
        """Notify the user about pending tasks."""
        pending = _pending_tasks(tasks)
        if not pending:
            return

        body = _format_item_list("Pending Tasks", pending, "(none)")
        self._show("Task Reminder", body)

    def show_goal_reminder(self, goals: list[dict]) -> None:
        """Notify the user about active goals."""
        active = _active_goals(goals)
        if not active:
            return

        body = _format_item_list("Goals", active, "(none)")
        self._show("Goal Reminder", body)

    def show_daily_briefing(
        self,
        goals: list[dict],
        tasks: list[dict],
        profile_text: str,
        news_data: dict | None = None,
    ) -> None:
        """Notify the user with the morning daily briefing."""
        if not self.daily_briefing_enabled():
            return

        body = self.build_daily_briefing(
            goals,
            tasks,
            profile_text,
            news_data=news_data,
        )
        self._show("ARYA Daily Briefing", body)


class NotificationScheduler(QObject):
    """Checks once per minute for morning notifications."""

    def __init__(
        self,
        notification_service: NotificationService,
        api_client: ApiClient | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self.notification_service = notification_service
        self.api_client = api_client or ApiClient()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_morning_notifications)
        self.timer.start(60_000)
        QTimer.singleShot(10_000, self.check_morning_notifications)

    def check_morning_notifications(self) -> None:
        """Send morning reminders once per day after the configured hour."""
        if not is_windows():
            return

        settings = settings_store.load_settings()
        if not settings.get("enable_notifications", False):
            return

        now = datetime.now()
        if now.hour < MORNING_HOUR:
            return

        today = now.date().isoformat()

        try:
            goals = self.api_client.get_goals()
            tasks = self.api_client.get_tasks()
            profile_data = self.api_client.get_profile()
            profile_text = profile_data.get("profile", "")
        except Exception:
            return

        news_data = None
        try:
            news_data = self.api_client.get_news()
        except Exception:
            news_data = None

        updated = False

        if settings.get("enable_daily_briefing", False):
            if settings.get("last_daily_briefing_date") != today:
                self.notification_service.show_daily_briefing(
                    goals,
                    tasks,
                    profile_text,
                    news_data=news_data,
                )
                settings["last_daily_briefing_date"] = today
                updated = True
        else:
            if settings.get("last_task_reminder_date") != today:
                self.notification_service.show_task_reminder(tasks)
                settings["last_task_reminder_date"] = today
                updated = True

            if settings.get("last_goal_reminder_date") != today:
                self.notification_service.show_goal_reminder(goals)
                settings["last_goal_reminder_date"] = today
                updated = True

        if updated:
            settings_store.save_settings(settings)
