from .tool_registry import registry
from .tool_schemas import ToolSchema, ToolParam, ParamType, ToolCategory, ToolResult
from app.database import SessionLocal
from app.models import ScheduledRoutine

def _schedule_routine(params: dict) -> ToolResult:
    command = params.get("command", "")
    cron_expr = params.get("cron_expr", "")
    
    if not command or not cron_expr:
        return ToolResult(False, "Missing command or cron_expr.", data={})
    
    db = SessionLocal()
    try:
        routine = ScheduledRoutine(command=command, cron_expr=cron_expr, is_active=1)
        db.add(routine)
        db.commit()
        db.refresh(routine)
        return ToolResult(True, f"Routine scheduled: '{command}' with cron '{cron_expr}'.", data={"id": routine.id})
    except Exception as e:
        return ToolResult(False, f"Failed to schedule routine: {e}", data={})
    finally:
        db.close()

registry.register(
    schema=ToolSchema(
        name="schedule_routine",
        description="Schedule a recurring autonomous command using cron syntax.",
        category=ToolCategory.SYSTEM,
        params=[
            ToolParam("command", ParamType.STRING, "The command for ARYA to execute (e.g. 'turn on the lights')", required=True),
            ToolParam("cron_expr", ParamType.STRING, "Cron syntax (e.g. '0 8 * * *' for 8 AM daily)", required=True)
        ],
        examples=["schedule 'turn on the lights' at 8am every day", "every minute say 'hello'"]
    ),
    handler=_schedule_routine,
)
