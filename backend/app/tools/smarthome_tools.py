from .tool_registry import registry
from .tool_schemas import ToolSchema, ToolParam, ParamType, ToolCategory, ToolResult
from app.smarthome_service import smarthome_service

def _control_lights(params: dict) -> ToolResult:
    action = params.get("action", "").lower()
    if action == "on":
        res = smarthome_service.turn_on_lights()
    elif action == "off":
        res = smarthome_service.turn_off_lights()
    else:
        return ToolResult(False, f"Invalid action: {action}. Must be 'on' or 'off'.", data={})
    
    return ToolResult(success=res.get("success", False), message=res.get("message", ""), data=res)

registry.register(
    schema=ToolSchema(
        name="control_lights",
        description="Turn the physical smart room lights ON or OFF.",
        category=ToolCategory.DEVICE,
        params=[ToolParam("action", ParamType.STRING, "Action to perform: 'on' or 'off'", required=True)],
        examples=["turn on the lights", "switch off the room lights", "dim the lights to 0"]
    ),
    handler=_control_lights,
)
