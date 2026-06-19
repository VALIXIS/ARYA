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
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(18, 18, 18, 18)

        self.profile_label = QLabel("No profile loaded yet.")
        self.profile_label.setObjectName("BodyText")
        self.profile_label.setWordWrap(True)
        panel_layout.addWidget(self.profile_label)
        panel_layout.addStretch()

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

        profile = data.get("profile", "No profile available.")
        self.profile_label.setText(profile)
        self.status_label.setText("Profile loaded")
