"""
profile_page.py
---------------
Profile page for ARYA Desktop.
"""

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from arya_desktop.api_client import ApiClient
from arya_desktop.ui.icons import ICONS, create_svg_icon
from PySide6.QtCore import Qt


class ProfilePage(QWidget):
    """Loads and displays the user profile from GET /profile."""

    def __init__(self, api_client: ApiClient | None = None):
        super().__init__()
        self.api_client = api_client or ApiClient()
        self.profile_label: QLabel
        self.status_label: QLabel
        self._build_ui()
        self.status_label.setText("Click Refresh to load profile.")

    def _build_ui(self) -> None:
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(36, 32, 36, 28)
        page_layout.setSpacing(18)

        header = QHBoxLayout()
        title_area = QVBoxLayout()

        title = QLabel("Profile")
        title.setObjectName("PageTitle")

        subtitle = QLabel("Loaded from /profile")
        subtitle.setObjectName("PageSubtitle")

        title_area.addWidget(title)
        title_area.addWidget(subtitle)

        refresh_button = QPushButton("Refresh")
        refresh_button.setObjectName("RefreshButton")
        refresh_button.clicked.connect(self.refresh)

        header.addLayout(title_area, 1)
        header.addWidget(refresh_button)

        self.status_label = QLabel("")
        self.status_label.setObjectName("PageSubtitle")

        panel = QFrame()
        panel.setObjectName("DataCard")
        self.content_layout = QVBoxLayout(panel)
        self.content_layout.setContentsMargins(18, 18, 18, 18)

        self.profile_label = QLabel()
        self.profile_label.setObjectName("BodyText")
        self.profile_label.setWordWrap(True)
        self.profile_label.hide()
        
        self.empty_container = QWidget()
        empty_layout = QVBoxLayout(self.empty_container)
        empty_layout.setAlignment(Qt.AlignCenter)
        
        icon_label = QLabel()
        icon = create_svg_icon(ICONS.get("EmptyState", ""), color="#4b5563")
        pixmap = icon.pixmap(48, 48)
        icon_label.setPixmap(pixmap)
        icon_label.setAlignment(Qt.AlignCenter)
        
        self.empty_text = QLabel("No profile loaded yet.")
        self.empty_text.setObjectName("PlaceholderText")
        self.empty_text.setAlignment(Qt.AlignCenter)
        
        empty_layout.addStretch()
        empty_layout.addWidget(icon_label)
        empty_layout.addWidget(self.empty_text)
        empty_layout.addStretch()

        self.content_layout.addWidget(self.profile_label)
        self.content_layout.addWidget(self.empty_container)
        self.content_layout.addStretch()

        scroll_area = QScrollArea()
        scroll_area.setObjectName("DataScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setWidget(panel)

        page_layout.addLayout(header)
        page_layout.addWidget(self.status_label)
        page_layout.addWidget(scroll_area, 1)

    def refresh(self) -> None:
        """Load the profile from the backend."""
        self.status_label.setText("Loading profile...")

        try:
            data = self.api_client.get_profile()
        except Exception as error:
            self.status_label.setText(f"Could not load profile: {error}")
            return

        profile = data.get("profile", "")
        if profile:
            self.empty_container.hide()
            self.profile_label.show()
            self.profile_label.setText(profile)
        else:
            self.profile_label.hide()
            self.empty_text.setText("Profile is empty.")
            self.empty_container.show()
            
        self.status_label.setText("Profile loaded")
