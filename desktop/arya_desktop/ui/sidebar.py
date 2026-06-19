"""
sidebar.py
----------
Sidebar navigation for ARYA Desktop.
"""

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from arya_desktop.ui.icons import ICONS, create_svg_icon


class Sidebar(QFrame):
    """Left navigation rail."""

    page_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(220)

        self.buttons: dict[str, QPushButton] = {}
        self.pages = ["Chat", "Tasks", "Goals", "Memories", "Profile", "Settings", "About"]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 14)
        layout.setSpacing(8)

        title = QLabel("ARYA")
        title.setObjectName("AppTitle")
        layout.addWidget(title)

        for page_name in self.pages:
            button = QPushButton(f"  {page_name}")
            button.setObjectName("NavButton")
            button.setCursor(Qt.PointingHandCursor)
            
            icon = create_svg_icon(ICONS.get(page_name, ""), color="#a3a6ae")
            button.setIcon(icon)
            button.setIconSize(QSize(20, 20))
            
            button.clicked.connect(lambda checked=False, name=page_name: self.select_page(name))
            self.buttons[page_name] = button
            layout.addWidget(button)

        layout.addStretch()
        self.select_page("Chat", emit_signal=False)

    def select_page(self, page_name: str, emit_signal: bool = True) -> None:
        """Mark a page active and optionally emit navigation."""
        for name, button in self.buttons.items():
            button.setProperty("active", name == page_name)
            button.style().unpolish(button)
            button.style().polish(button)

        if emit_signal:
            self.page_selected.emit(page_name)
