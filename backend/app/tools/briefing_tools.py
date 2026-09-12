"""
Morning Briefing Tool for ARYA.
"""

from .tool_registry import registry
from .tool_schemas import ToolCategory, ToolSchema, ToolResult
from ..briefing_service import generate_morning_briefing


def _get_morning_briefing(params: dict) -> ToolResult:
    """Generate and return a unified morning briefing."""
    data = generate_morning_briefing()
    return ToolResult(
        success=True,
        message=data["briefing"],
        data=data
    )


# Register Briefing Tool
registry.register(
    schema=ToolSchema(
        name="generate_morning_briefing",
        description="Generate a complete morning briefing combining Weather, To-Do Tasks, Calendar, and Email summaries.",
        category=ToolCategory.SYSTEM,
        params=[],
        examples=[
            "give me my morning briefing",
            "what's my schedule and briefing for today?",
            "good morning briefing",
            "start my day"
        ],
    ),
    handler=_get_morning_briefing,
)
