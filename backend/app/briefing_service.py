"""
Autonomous Morning Briefing Service for ARYA.
Aggregates Weather, To-Do Tasks, Google/Outlook Calendar, and Unread Emails
into a unified J.A.R.V.I.S-style executive report.
"""

from typing import Dict, Any
from .weather_service import get_weather_data
from .task_service import list_tasks
from .google_service import get_calendar_events as get_g_events, get_unread_emails as get_g_emails
from .microsoft_service import get_outlook_calendar as get_ms_events, get_outlook_emails as get_ms_emails


def generate_morning_briefing() -> Dict[str, Any]:
    """Generate a comprehensive morning briefing."""
    # 1. Weather
    weather = get_weather_data("Guntur")
    temp = weather.get("temperature", "N/A")
    cond = weather.get("condition", "N/A")
    location = weather.get("location", "Guntur")

    weather_summary = f"{location} is currently {temp} with {cond}."

    # 2. To-Do Tasks
    active_tasks = list_tasks("active")
    task_count = len(active_tasks)
    if task_count == 0:
        task_summary = "Your to-do list is completely clear, Sir."
    else:
        top_tasks = ", ".join([f"'{t['title']}'" for t in active_tasks[:3]])
        task_summary = f"You have {task_count} active task(s). Top priority: {top_tasks}."

    # 3. Google Calendar
    g_cal = get_g_events(days=1)
    g_events = g_cal.get("events", [])
    if g_cal.get("connected") and g_events:
        cal_summary = f"Google Calendar shows {len(g_events)} event(s) today."
    elif not g_cal.get("connected"):
        cal_summary = "Google Calendar is not linked yet."
    else:
        cal_summary = "No Google Calendar events scheduled for today."

    # 4. Emails
    g_mail = get_g_emails(max_results=3)
    unread_g = g_mail.get("count", 0) if g_mail.get("connected") else 0

    ms_mail = get_ms_emails(max_results=3)
    unread_ms = ms_mail.get("count", 0) if ms_mail.get("connected") else 0

    total_unread = unread_g + unread_ms
    email_summary = f"You have {total_unread} unread email(s) across your accounts." if total_unread > 0 else "Your inbox is completely clear."

    # Synthesize Executive Briefing
    full_briefing = (
        f"Good morning, Sir! Here is your daily briefing for today:\n\n"
        f"🌤️ **Weather**: {weather_summary}\n"
        f"📋 **Tasks**: {task_summary}\n"
        f"📅 **Schedule**: {cal_summary}\n"
        f"📧 **Inbox**: {email_summary}\n\n"
        f"All systems operational. How would you like to begin?"
    )

    return {
        "success": True,
        "briefing": full_briefing,
        "weather": weather,
        "tasks": active_tasks,
        "calendar_count": len(g_events),
        "unread_emails": total_unread
    }
