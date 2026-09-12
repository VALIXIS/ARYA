"""
Google Workspace Tools for ARYA — Gmail and Google Calendar operations.
"""

from .tool_registry import registry
from .tool_schemas import ToolCategory, ToolParam, ParamType, ToolSchema, ToolResult
from ..google_service import get_unread_emails, get_calendar_events, is_google_connected


def _read_google_emails(params: dict) -> ToolResult:
    """Read unread emails from Gmail."""
    res = get_unread_emails(max_results=5)
    if not res.get("connected"):
        return ToolResult(
            success=False,
            message="Google Account is not connected yet, Sir. To enable Gmail reading, place your `google_credentials.json` in the backend folder.",
            data=res
        )

    if not res.get("success"):
        return ToolResult(False, f"Failed to fetch Gmail emails: {res.get('error')}", data=res)

    emails = res.get("emails", [])
    if not emails:
        return ToolResult(True, "You have no unread emails in Gmail right now, Sir.", data=res)

    formatted = "\n".join([f"- From: {e['sender']} | Subject: {e['subject']}\n  Snippet: {e['snippet']}" for e in emails])
    msg = f"You have {len(emails)} unread email(s):\n{formatted}"

    return ToolResult(True, message=msg, data=res)


def _get_google_calendar(params: dict) -> ToolResult:
    """Fetch events from Google Calendar."""
    days = int(params.get("days", 1))
    res = get_calendar_events(days=days)

    if not res.get("connected"):
        return ToolResult(
            success=False,
            message="Google Account is not connected yet, Sir. Place your `google_credentials.json` in the backend folder to sync your Google Calendar.",
            data=res
        )

    if not res.get("success"):
        return ToolResult(False, f"Failed to fetch Google Calendar events: {res.get('error')}", data=res)

    events = res.get("events", [])
    if not events:
        return ToolResult(True, f"No upcoming events scheduled on your Google Calendar for the next {days} day(s), Sir.", data=res)

    formatted = "\n".join([f"- {e['summary']} at {e['start']}" for e in events])
    msg = f"Here are your upcoming Google Calendar events:\n{formatted}"

    return ToolResult(True, message=msg, data=res)


# Register Google Tools
registry.register(
    schema=ToolSchema(
        name="read_gmail",
        description="Read unread emails from Gmail inbox.",
        category=ToolCategory.SYSTEM,
        params=[ToolParam("max_results", ParamType.INTEGER, "Maximum emails to fetch (default 5)", required=False, default=5)],
        examples=["read my emails", "check gmail inbox", "do I have any new emails?"],
    ),
    handler=_read_google_emails,
)

registry.register(
    schema=ToolSchema(
        name="get_google_calendar",
        description="Get events from Google Calendar.",
        category=ToolCategory.SYSTEM,
        params=[ToolParam("days", ParamType.INTEGER, "Days ahead to look up (default 1)", required=False, default=1)],
        examples=["what is on my google calendar today?", "my schedule for today", "check google calendar"],
    ),
    handler=_get_google_calendar,
)
