"""
system_tools.py
---------------
System-level tools that return information without calling the LLM.

Registers 2 tools on import:
    get_time, get_date
"""

from datetime import datetime

from .tool_registry import registry
from .tool_schemas import ToolSchema, ToolCategory, ToolResult

# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def _get_time(_params: dict) -> ToolResult:
    now = datetime.now()
    time_str = now.strftime("%I:%M %p")   # e.g. "08:35 PM"
    print(f"[TOOL] get_time -> {time_str}")
    return ToolResult(success=True, message=f"The current time is {time_str}.")


def _get_date(_params: dict) -> ToolResult:
    now = datetime.now()
    date_str = now.strftime("%A, %d %B %Y")   # e.g. "Friday, 20 June 2025"
    print(f"[TOOL] get_date -> {date_str}")
    return ToolResult(success=True, message=f"Today is {date_str}.")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

registry.register(
    schema=ToolSchema(
        name="get_time",
        description="Return the current local time.",
        category=ToolCategory.SYSTEM,
        params=[],
        examples=["what time is it", "tell me the time", "current time"],
    ),
    handler=_get_time,
)

registry.register(
    schema=ToolSchema(
        name="get_date",
        description="Return today's date.",
        category=ToolCategory.SYSTEM,
        params=[],
        examples=["what is today's date", "what day is it", "current date"],
    ),
    handler=_get_date,
)
