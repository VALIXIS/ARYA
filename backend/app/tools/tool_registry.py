"""
tool_registry.py
----------------
Central registry that owns all registered tools.

Usage
-----
Tools register themselves on import:

    from app.tools.tool_registry import registry
    from app.tools.tool_schemas import ToolSchema, ToolCategory, ToolParam, ParamType

    registry.register(
        schema=ToolSchema(name="search_youtube", ...),
        handler=lambda params: ...,
    )

The registry is then used by tool_executor.py to dispatch calls.
"""

from __future__ import annotations

from typing import Callable, Any

from .tool_schemas import ToolSchema, ToolCategory, ToolResult


class _ToolEntry:
    """Internal pairing of a schema with its callable handler."""
    __slots__ = ("schema", "handler")

    def __init__(self, schema: ToolSchema, handler: Callable[[dict[str, Any]], ToolResult]):
        self.schema = schema
        self.handler = handler


class ToolRegistry:
    """Singleton-style registry holding all available tools."""

    def __init__(self) -> None:
        self._tools: dict[str, _ToolEntry] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        schema: ToolSchema,
        handler: Callable[[dict[str, Any]], ToolResult],
    ) -> None:
        """Register a tool.  Raises if a tool with the same name already exists."""
        if schema.name in self._tools:
            raise ValueError(f"Tool already registered: {schema.name!r}")
        self._tools[schema.name] = _ToolEntry(schema=schema, handler=handler)
        print(f"[TOOLS] Registered: {schema.name!r} [{schema.category.value}]")

    # ------------------------------------------------------------------
    # Look-up helpers
    # ------------------------------------------------------------------

    def has(self, name: str) -> bool:
        return name in self._tools

    def get_schema(self, name: str) -> ToolSchema | None:
        entry = self._tools.get(name)
        return entry.schema if entry else None

    def get_handler(self, name: str) -> Callable | None:
        entry = self._tools.get(name)
        return entry.handler if entry else None

    def all_schemas(self) -> list[ToolSchema]:
        return [e.schema for e in self._tools.values()]

    def schemas_by_category(self, category: ToolCategory) -> list[ToolSchema]:
        return [e.schema for e in self._tools.values() if e.schema.category == category]

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def summary_for_prompt(self) -> str:
        """
        Build a compact tool list suitable for embedding in an LLM prompt.
        Format: name: description  (one tool per line)
        """
        lines = [
            f"  {e.schema.name}: {e.schema.description}"
            for e in self._tools.values()
        ]
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._tools)

    def __repr__(self) -> str:
        return f"<ToolRegistry tools={self.names()}>"


# Module-level singleton — import this in all other tool files.
registry = ToolRegistry()
