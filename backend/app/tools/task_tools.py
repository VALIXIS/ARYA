"""
Task Tools for ARYA — Exposes To-Do operations to the AI planner.
"""

from .tool_registry import registry
from .tool_schemas import ToolCategory, ToolParam, ParamType, ToolSchema, ToolResult
from ..task_service import create_task, list_tasks, complete_task, delete_task


def _add_task(params: dict) -> ToolResult:
    """Add a new task to the user's to-do list."""
    title = params.get("title", "").strip()
    if not title:
        return ToolResult(False, "Task title cannot be empty.")

    res = create_task(title)
    return ToolResult(
        success=True,
        message=f"Added task: '{res['title']}'",
        data=res
    )


def _list_tasks(params: dict) -> ToolResult:
    """List pending or completed tasks."""
    status = params.get("status", "active")
    tasks = list_tasks(status)

    if not tasks:
        msg = f"No {status} tasks found, Sir."
    else:
        formatted = "\n".join([f"- [ID {t['id']}] {t['title']} ({t['status']})" for t in tasks])
        msg = f"Here are your {status} tasks:\n{formatted}"

    return ToolResult(
        success=True,
        message=msg,
        data={"tasks": tasks}
    )


def _complete_task(params: dict) -> ToolResult:
    """Mark a task as done."""
    task_id = params.get("task_identifier", "").strip()
    if not task_id:
        return ToolResult(False, "Please specify which task to mark complete.")

    res = complete_task(task_id)
    if res.get("success"):
        return ToolResult(True, f"Completed task: '{res['task']['title']}'", data=res)
    else:
        return ToolResult(False, res.get("error", "Task not found."))


def _delete_task(params: dict) -> ToolResult:
    """Remove a task from the list."""
    task_id = params.get("task_identifier", "").strip()
    if not task_id:
        return ToolResult(False, "Please specify which task to delete.")

    res = delete_task(task_id)
    if res.get("success"):
        return ToolResult(True, f"Deleted task: '{res['deleted_task']}'", data=res)
    else:
        return ToolResult(False, res.get("error", "Task not found."))


# Register Task Tools
registry.register(
    schema=ToolSchema(
        name="add_task",
        description="Add a new item/task to the user's To-Do list.",
        category=ToolCategory.SYSTEM,
        params=[ToolParam("title", ParamType.STRING, "Task description/title", required=True)],
        examples=["add task submit assignment", "remind me to buy groceries", "add to my to-do list: finish project"],
    ),
    handler=_add_task,
)

registry.register(
    schema=ToolSchema(
        name="list_tasks",
        description="List all active or completed To-Do tasks.",
        category=ToolCategory.SYSTEM,
        params=[ToolParam("status", ParamType.STRING, "'active', 'completed', or 'all'", required=False, default="active")],
        examples=["what are my tasks for today?", "list my to-do items", "show completed tasks"],
    ),
    handler=_list_tasks,
)

registry.register(
    schema=ToolSchema(
        name="complete_task",
        description="Mark a To-Do task as finished/completed by ID or title.",
        category=ToolCategory.SYSTEM,
        params=[ToolParam("task_identifier", ParamType.STRING, "Task ID or matching title", required=True)],
        examples=["mark task 1 as done", "finish task buy groceries", "complete task assignment"],
    ),
    handler=_complete_task,
)

registry.register(
    schema=ToolSchema(
        name="delete_task",
        description="Delete a To-Do task by ID or title.",
        category=ToolCategory.SYSTEM,
        params=[ToolParam("task_identifier", ParamType.STRING, "Task ID or matching title", required=True)],
        examples=["delete task 2", "remove task buy groceries"],
    ),
    handler=_delete_task,
)
