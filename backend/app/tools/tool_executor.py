"""
tool_executor.py
----------------
Internal dispatch layer.

Validates parameters, calls the registered handler, and enforces that every
tool returns a ToolResult — never a raw value or silent exception.
"""

from __future__ import annotations

from .tool_registry import registry
from .tool_schemas import ToolResult


def run_tool(name: str, params: dict) -> ToolResult:
    """
    Execute a registered tool by name with the given params dict.

    Logs:
        [TOOL] Executing <name> params=<params>
        [TOOL] Success: <message>
        [TOOL] Failed: <error>

    Never raises — wraps all exceptions into a failure ToolResult.
    """
    print(f"[TOOL] Executing {name!r} params={params}")

    if not registry.has(name):
        err = f"Unknown tool: {name!r}. Available: {registry.names()}"
        print(f"[TOOL] Failed: {err}")
        return ToolResult(success=False, message=f"Unknown tool '{name}'.", error=err)

    handler = registry.get_handler(name)
    schema  = registry.get_schema(name)

    # --- Parameter validation ---
    for param in schema.params:
        if param.required and param.name not in params:
            # Inject default if one is defined
            if param.default is not None:
                params[param.name] = param.default
            else:
                err = f"Missing required param '{param.name}' for tool '{name}'"
                print(f"[TOOL] Failed: {err}")
                return ToolResult(success=False, message=err, error=err)

    # --- Execution ---
    try:
        result: ToolResult = handler(params)
    except Exception as exc:
        err = f"{type(exc).__name__}: {exc}"
        print(f"[TOOL] Failed: {name!r} raised {err}")
        return ToolResult(success=False, message=f"Tool '{name}' failed: {exc}", error=err)

    if result.success:
        print(f"[TOOL] Success: {result.message}")
    else:
        print(f"[TOOL] Failed: {result.error or result.message}")

    return result
