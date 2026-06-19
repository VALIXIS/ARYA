"""
system_tray.py
--------------
Windows-compatible system tray support for ARYA Desktop.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget

from arya_desktop.config import APP_NAME

TRAY_NOTIFICATION = "ARYA is running in the background"


def build_tray_icon() -> QIcon:
    """Build a simple ARYA tray icon without external asset files."""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor("#5B8CFF"))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(4, 4, size - 8, size - 8)

    painter.setPen(QColor("#FFFFFF"))
    font = painter.font()
    font.setPixelSize(36)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "A")
    painter.end()

    return QIcon(pixmap)


class AryaSystemTray:
    """System tray icon, menu, and background notifications."""

    def __init__(self, window: QWidget):
        self.window = window
        self.is_exiting = False
        self.enabled = QSystemTrayIcon.isSystemTrayAvailable()

        if not self.enabled:
            return

        self.icon = build_tray_icon()
        window.setWindowIcon(self.icon)

        self.tray_icon = QSystemTrayIcon(self.icon, window)
        self.tray_icon.setToolTip(APP_NAME)

        tray_menu = QMenu()
        open_action = tray_menu.addAction("Open ARYA")
        exit_action = tray_menu.addAction("Exit ARYA")

        open_action.triggered.connect(self.open_window)
        exit_action.triggered.connect(self.exit_application)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._handle_activation)
        self.tray_icon.show()

    def open_window(self) -> None:
        """Show and focus the main ARYA window."""
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def exit_application(self) -> None:
        """Exit ARYA completely."""
        self.is_exiting = True
        if self.enabled:
            self.tray_icon.hide()
        QApplication.quit()

    def hide_window_to_tray(self) -> None:
        """Hide the window and notify the user that ARYA keeps running."""
        self.window.hide()
        if self.enabled:
            self.tray_icon.showMessage(
                APP_NAME,
                TRAY_NOTIFICATION,
                QSystemTrayIcon.Information,
                3000,
            )

    def _handle_activation(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Restore the window when the tray icon is double-clicked."""
        if reason == QSystemTrayIcon.DoubleClick:
            self.open_window()

    def get_tray_icon(self) -> QSystemTrayIcon | None:
        """Return the tray icon used for Windows notifications."""
        if not self.enabled:
            return None
        return self.tray_icon
