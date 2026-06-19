"""
tool_schemas.py
---------------
Defines the data structures that describe a tool.

A ToolSchema tells ARYA:
  - what the tool is called
  - what it does (for the LLM to decide when to use it)
  - what parameters it accepts
  - what category it belongs to

This module is pure data — no imports from other tool modules.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ToolCategory(str, Enum):
    """High-level grouping of tools."""
    BROWSER  = "browser"
    APP      = "app"
    FILE     = "file"
    SYSTEM   = "system"


class ParamType(str, Enum):
    """Supported parameter types."""
    STRING  = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    PATH    = "path"
    URL     = "url"


@dataclass
class ToolParam:
    """Describes one parameter of a tool."""
    name: str
    type: ParamType
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolResult:
    """Returned by every tool execution."""
    success: bool
    message: str                        # Human-readable summary shown to user
    detail: str = ""                    # Extended log / debug info
    error: str = ""                     # Non-empty if success=False


@dataclass
class ToolSchema:
    """Full description of one tool."""
    name: str                           # Unique identifier, e.g. "search_youtube"
    description: str                    # One-line description for LLM routing
    category: ToolCategory
    params: list[ToolParam] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)  # Example user phrases

    def to_dict(self) -> dict:
        """Serialise to a plain dict (useful for building LLM prompts)."""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "params": [
                {
                    "name": p.name,
                    "type": p.type.value,
                    "description": p.description,
                    "required": p.required,
                }
                for p in self.params
            ],
            "examples": self.examples,
        }
