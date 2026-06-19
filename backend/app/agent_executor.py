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

    Each dict must have:
        {"tool": str, "params": dict}

    Returns a single reply string joining all results.

    Logs:
        [AGENT] Executing step <n>/<total>: <tool>
        [AGENT] Step <n> succeeded: <message>
        [AGENT] Step <n> failed: <error>
        [AGENT] Execution complete: <n> ok, <n> failed
    """
    if not plan:
        return ""

    total = len(plan)
    results: list[ToolResult] = []

    for i, step in enumerate(plan, start=1):
        tool_name = step.get("tool", "")
        params    = step.get("params", {})

        print(f"[AGENT] Executing step {i}/{total}: {tool_name!r} params={params}")

        result = run_tool(tool_name, params)
        results.append(result)

        if result.success:
            print(f"[AGENT] Step {i} succeeded: {result.message}")
        else:
            print(f"[AGENT] Step {i} failed: {result.error or result.message}")

    ok_count   = sum(1 for r in results if r.success)
    fail_count = total - ok_count
    print(f"[AGENT] Execution complete: {ok_count} ok, {fail_count} failed")

    # Build reply — join all messages on separate lines
    return "\n".join(r.message for r in results)
