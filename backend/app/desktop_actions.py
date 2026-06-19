"""
desktop_actions.py
------------------
Fixed desktop actions ARYA can run on Windows.
Only known actions are supported.
"""

import os
import subprocess


def open_chrome() -> None:
    """Open Google Chrome."""
    subprocess.Popen(["cmd", "/c", "start", "", "chrome"])


def open_vscode() -> None:
    """Open Visual Studio Code."""
    subprocess.Popen(["cmd", "/c", "start", "", "code"])


def open_file_explorer() -> None:
    """Open File Explorer."""
    os.startfile(os.path.expanduser("~"))


def open_downloads_folder() -> None:
    """Open the user's Downloads folder."""
    os.startfile(os.path.join(os.path.expanduser("~"), "Downloads"))


def run_desktop_action(action: str) -> str:
    """Run a supported desktop action and return a confirmation message."""
    actions = {
        "chrome": (open_chrome, "Opening Chrome."),
        "vscode": (open_vscode, "Opening VS Code."),
        "file_explorer": (open_file_explorer, "Opening File Explorer."),
        "downloads": (open_downloads_folder, "Opening Downloads."),
    }

    if action not in actions:
        return "I do not know that desktop action."

    action_fn, message = actions[action]
    action_fn()
    return message
