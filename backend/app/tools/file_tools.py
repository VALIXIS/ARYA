"""
file_tools.py
-------------
File system tools: create folder, open folder, create file with content.

Registers 3 tools on import:
    create_folder, open_folder, create_file
"""

import os
import sys
from pathlib import Path

from .tool_registry import registry
from .tool_schemas import ToolSchema, ToolCategory, ToolParam, ParamType, ToolResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SPECIAL_FOLDERS: dict[str, Path] = {
    "desktop":   Path.home() / "Desktop",
    "downloads": Path.home() / "Downloads",
    "documents": Path.home() / "Documents",
    "pictures":  Path.home() / "Pictures",
    "music":     Path.home() / "Music",
    "videos":    Path.home() / "Videos",
    "home":      Path.home(),
    "~":         Path.home(),
}


def _resolve_path(raw: str) -> Path:
    """
    Resolve a user-supplied path string.
    Handles special names (desktop, downloads, …), ~ expansion, and absolute paths.
    Relative paths are resolved against the user's home directory.
    """
    normalized = raw.strip().lower()

    # Special names like "desktop", "downloads"
    for keyword, resolved in _SPECIAL_FOLDERS.items():
        if normalized == keyword:
            return resolved

    # Check if it starts with a special folder name (e.g. "desktop/Projects")
    for keyword, base in _SPECIAL_FOLDERS.items():
        if normalized.startswith(keyword + "/") or normalized.startswith(keyword + "\\"):
            remainder = raw.strip()[len(keyword):].lstrip("/\\")
            return base / remainder

    path = Path(raw.strip()).expanduser()
    if path.is_absolute():
        return path

    # If it's just a bare name (no directory), default to Desktop
    if path.parent == Path("."):
        return Path.home() / "Desktop" / path

    # Relative path with directory — anchor to home
    return Path.home() / path


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def _create_folder(params: dict) -> ToolResult:
    path_str: str = params["path"].strip()
    target = _resolve_path(path_str)
    print(f"[TOOL] create_folder: {target}")

    if target.exists():
        return ToolResult(
            success=True,
            message=f"Folder already exists at '{target}'.",
            detail=str(target),
        )

    try:
        target.mkdir(parents=True, exist_ok=True)
        if target.exists():
            return ToolResult(success=True, message=f"Created folder '{target}'.", detail=str(target))
        return ToolResult(success=False, message="Folder creation reported no error but path does not exist.", error="Post-creation check failed")
    except Exception as exc:
        err = f"{type(exc).__name__}: {exc}"
        return ToolResult(success=False, message=f"Failed to create folder: {exc}", error=err)


def _open_folder(params: dict) -> ToolResult:
    path_str: str = params["path"].strip()
    target = _resolve_path(path_str)
    print(f"[TOOL] open_folder: {target}")

    if not target.exists():
        err = f"Folder not found: {target}"
        return ToolResult(success=False, message=err, error=err)

    try:
        if sys.platform == "win32":
            os.startfile(str(target))
        else:
            import subprocess
            subprocess.Popen(["xdg-open", str(target)])
        return ToolResult(success=True, message=f"Opened folder '{target}'.", detail=str(target))
    except Exception as exc:
        err = f"{type(exc).__name__}: {exc}"
        return ToolResult(success=False, message=f"Failed to open folder: {exc}", error=err)


def _create_file(params: dict) -> ToolResult:
    path_str: str = params["path"].strip()
    content: str = params.get("content", "")
    target = _resolve_path(path_str)
    print(f"[TOOL] create_file: {target} (content length={len(content)})")

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

        if target.exists():
            return ToolResult(
                success=True,
                message=f"Created file '{target}'." if not content else f"Created file '{target}' with content.",
                detail=str(target),
            )
        return ToolResult(success=False, message="File write reported no error but file not found.", error="Post-write check failed")
    except Exception as exc:
        err = f"{type(exc).__name__}: {exc}"
        return ToolResult(success=False, message=f"Failed to create file: {exc}", error=err)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

registry.register(
    schema=ToolSchema(
        name="create_folder",
        description="Create a new folder/directory at a specified path.",
        category=ToolCategory.FILE,
        params=[ToolParam("path", ParamType.PATH, "Path or name of folder to create, e.g. 'Desktop/Projects'")],
        examples=["create a folder called Projects on desktop", "make folder Notes", "create downloads/Work folder"],
    ),
    handler=_create_folder,
)

registry.register(
    schema=ToolSchema(
        name="open_folder",
        description="Open a folder in the system file explorer.",
        category=ToolCategory.FILE,
        params=[ToolParam("path", ParamType.PATH, "Folder name or path to open, e.g. 'downloads', 'Desktop'")],
        examples=["open downloads folder", "show my documents", "open desktop"],
    ),
    handler=_open_folder,
)

registry.register(
    schema=ToolSchema(
        name="create_file",
        description="Create a new text file, optionally with content.",
        category=ToolCategory.FILE,
        params=[
            ToolParam("path",    ParamType.PATH,   "File path or name, e.g. 'Desktop/notes.txt'"),
            ToolParam("content", ParamType.STRING,  "Text content to write into the file", required=False, default=""),
        ],
        examples=["create notes.txt", "create notes.txt with text hello world", "make a file called todo.txt saying Buy milk"],
    ),
    handler=_create_file,
)
