"""
main.py
-------
Entry point for ARYA Desktop.
"""

import logging
import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QSystemTrayIcon


if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from arya_desktop.config import ARYA_LOG
from arya_desktop.ui.main_window import MainWindow
from arya_desktop.ui.theme import dark_theme
from arya_desktop.ollama_manager import ensure_ollama
from arya_desktop.backend_manager import ensure_backend

log = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Set up file logging for the ARYA desktop startup sequence."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
        handlers=[
            logging.FileHandler(ARYA_LOG, encoding="utf-8"),
        ],
    )


def main() -> int:
    """Launch the ARYA desktop application."""
    _configure_logging()

    app = QApplication(sys.argv)
    log.info(f"[STARTUP] Desktop PID: {os.getpid()}")
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(dark_theme())

    # --- Startup sequence: Ollama → Backend ---
    ollama_status = ensure_ollama()
    backend_status = "failed"
    if ollama_status != "failed":
        backend_status = ensure_backend()
    log.info("[STARTUP] Startup complete")

    window = MainWindow()
    window.showNormal()
    window.raise_()
    window.activateWindow()

    # --- Tray notifications for startup results ---
    tray = window.system_tray.get_tray_icon()
    if tray is not None:
        if ollama_status == "failed":
            tray.showMessage(
                "ARYA",
                "Ollama failed to start",
                QSystemTrayIcon.Warning,
                5000,
            )
        elif backend_status == "failed":
            tray.showMessage(
                "ARYA",
                "Backend failed to start",
                QSystemTrayIcon.Warning,
                5000,
            )
        elif ollama_status == "started":
            tray.showMessage(
                "ARYA",
                "Ollama started",
                QSystemTrayIcon.Information,
                5000,
            )
        elif backend_status == "started":
            tray.showMessage(
                "ARYA",
                "ARYA backend started",
                QSystemTrayIcon.Information,
                5000,
            )

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
