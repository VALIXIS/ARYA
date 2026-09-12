"""
Microsoft Tools for ARYA — Outlook Mail & Calendar.
"""

from .tool_registry import registry
from .tool_schemas import ToolCategory, ToolParam, ParamType, ToolSchema, ToolResult
from ..microsoft_service import get_outlook_emails, get_outlook_calendar


def _read_outlook_emails(params: dict) -> ToolResult:
    """Read unread Outlook emails."""
    res = get_outlook_emails()
    if not res.get("connected"):
        return ToolResult(False, "Microsoft Account is not connected yet, Sir.", data=res)

    if not res.get("success"):
        return ToolResult(False, f"Failed to fetch Outlook emails: {res.get('error')}", data=res)

    emails = res.get("emails", [])
    if not emails:
        return ToolResult(True, "No unread Outlook emails, Sir.", data=res)

    formatted = "\n".join([f"- From: {e['sender']} | Subject: {e['subject']}" for e in emails])
    return ToolResult(True, f"You have {len(emails)} unread Outlook email(s):\n{formatted}", data=res)


def _get_outlook_calendar(params: dict) -> ToolResult:
    """Fetch Outlook calendar events."""
    days = int(params.get("days", 1))
    res = get_outlook_calendar(days=days)
    if not res.get("connected"):
        return ToolResult(False, "Microsoft Account is not connected yet, Sir.", data=res)

    events = res.get("events", [])
    if not events:
        return ToolResult(True, f"No Outlook events scheduled for the next {days} day(s), Sir.", data=res)

    formatted = "\n".join([f"- {e['summary']} at {e['start']}" for e in events])
    return ToolResult(True, f"Outlook Calendar events:\n{formatted}", data=res)


# Register MS Tools
registry.register(
    schema=ToolSchema(
        name="read_outlook_emails",
        description="Read unread emails from Microsoft Outlook inbox.",
        category=ToolCategory.SYSTEM,
        params=[],
        examples=["read my outlook emails", "check outlook inbox"],
    ),
    handler=_read_outlook_emails,
)

registry.register(
    schema=ToolSchema(
        name="get_outlook_calendar",
        description="Get events from Microsoft Outlook Calendar.",
        category=ToolCategory.SYSTEM,
        params=[ToolParam("days", ParamType.INTEGER, "Days ahead", required=False, default=1)],
        examples=["check my outlook calendar", "outlook meetings for today"],
    ),
    handler=_get_outlook_calendar,
)
