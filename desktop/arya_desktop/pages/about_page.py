"""
about_page.py
-------------
About page for ARYA Desktop.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from arya_desktop import backend_manager, notification_service, ollama_manager, startup_manager


class AboutPage(QWidget):
    """Displays information about ARYA and system status."""

    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self) -> None:
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(36, 32, 36, 28)
        page_layout.setSpacing(18)

        title = QLabel("About")
        title.setObjectName("PageTitle")

        subtitle = QLabel("Adaptive Reasoning for Your Ambitions")
        subtitle.setObjectName("PageSubtitle")

        # Version Info
        version_panel = QFrame()
        version_panel.setObjectName("DataCard")
        version_layout = QVBoxLayout(version_panel)
        version_layout.setContentsMargins(18, 18, 18, 18)
        version_layout.setSpacing(8)

        version_label = QLabel("ARYA v1.0.2")
        version_label.setObjectName("PlaceholderTitle")
        
        description_label = QLabel("An advanced AI assistant integrating Ollama models and a FastAPI backend to provide seamless, private, and powerful reasoning on your local machine.")
        description_label.setObjectName("BodyText")
        description_label.setWordWrap(True)
        
        version_layout.addWidget(version_label)
        version_layout.addWidget(description_label)

        # System Status
        status_panel = QFrame()
        status_panel.setObjectName("DataCard")
        status_layout = QVBoxLayout(status_panel)
        status_layout.setContentsMargins(18, 18, 18, 18)
        status_layout.setSpacing(12)

        status_title = QLabel("System Status")
        status_title.setObjectName("PlaceholderTitle")
        status_layout.addWidget(status_title)
        
        ollama_status = "Active" if ollama_manager._is_healthy() else "Inactive"
        backend_status = "Active" if backend_manager._is_healthy() else "Inactive"
        notifications_status = "Active" if notification_service.is_windows() else "Inactive"
        auto_start_status = "Active" if startup_manager.is_startup_enabled() else "Inactive"
        
        def add_status_row(name: str, status: str):
            row = QHBoxLayout()
            name_label = QLabel(name)
            name_label.setObjectName("BodyText")
            
            status_label = QLabel(status)
            status_label.setObjectName("MetaText")
            if status == "Active":
                status_label.setStyleSheet("color: #4ade80; font-weight: bold;")
            else:
                status_label.setStyleSheet("color: #f87171; font-weight: bold;")
                
            row.addWidget(name_label)
            row.addStretch()
            row.addWidget(status_label)
            status_layout.addLayout(row)

        add_status_row("Ollama", ollama_status)
        add_status_row("Backend", backend_status)
        add_status_row("Notifications", notifications_status)
        add_status_row("Auto Start", auto_start_status)

        page_layout.addWidget(title)
        page_layout.addWidget(subtitle)
        page_layout.addWidget(version_panel)
        page_layout.addWidget(status_panel)
        page_layout.addStretch()
