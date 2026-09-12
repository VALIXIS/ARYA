"""
agent_executor.py
-----------------
Executes a plan produced by agent_planner.plan().

Calls tool_executor.run_tool() for each step sequentially.
Collects ToolResult objects and assembles a final human-readable reply.

A step failure is reported clearly — no step ever claims success unless
the underlying OS operation returned success=True.
"""

from __future__ import annotations

from .tools.tool_executor import run_tool
from .tools.tool_schemas import ToolResult


def execute(plan: list[dict]) -> str:
    """
    Execute a list of tool-call dicts sequentially.
    Broadcasts real-time events to connected WebSockets.
    """
    if not plan:
        return ""

    import asyncio
    from .ws_manager import ws_hub

    total = len(plan)
    results: list[ToolResult] = []

    def _broadcast_sync(event: dict):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(ws_hub.broadcast_to_clients(event))
            else:
                loop.run_until_complete(ws_hub.broadcast_to_clients(event))
        except Exception:
            pass

    for i, step in enumerate(plan, start=1):
        tool_name = step.get("tool", "")
        params    = step.get("params", {})

        print(f"[AGENT] Executing step {i}/{total}: {tool_name!r} params={params}")

        _broadcast_sync({
            "type": "agent_execution",
            "stage": "step_start",
            "step": i,
            "total": total,
            "tool": tool_name,
            "params": params,
        })

        result = run_tool(tool_name, params)
        results.append(result)

        if result.success:
            print(f"[AGENT] Step {i} succeeded: {result.message}")
            _broadcast_sync({
                "type": "agent_execution",
                "stage": "step_success",
                "step": i,
                "tool": tool_name,
                "message": result.message,
            })
        else:
            print(f"[AGENT] Step {i} failed: {result.error or result.message}")
            _broadcast_sync({
                "type": "agent_execution",
                "stage": "step_failed",
                "step": i,
                "tool": tool_name,
                "error": result.error or result.message,
            })

    ok_count   = sum(1 for r in results if r.success)
    fail_count = total - ok_count
    print(f"[AGENT] Execution complete: {ok_count} ok, {fail_count} failed")

    _broadcast_sync({
        "type": "agent_execution",
        "stage": "execution_complete",
        "ok": ok_count,
        "failed": fail_count,
    })

    # Build reply — join all messages on separate lines
    return "\n".join(r.message for r in results)

execute_plan = execute


