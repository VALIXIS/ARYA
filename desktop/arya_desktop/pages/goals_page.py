"""
goals_page.py
-------------
Goals page for ARYA Desktop.
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


class GoalsPage(QWidget):
    """Loads and displays goals from GET /goals."""

    def __init__(self, api_client: ApiClient | None = None):
        super().__init__()
        self.api_client = api_client or ApiClient()
        self.list_layout: QVBoxLayout
        self.status_label: QLabel
        self._build_ui()
        self.status_label.setText("Click Refresh to load goals.")

    def _build_ui(self) -> None:
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(36, 32, 36, 28)
        page_layout.setSpacing(18)

        header = QHBoxLayout()
        title_area = QVBoxLayout()

        title = QLabel("Goals")
        title.setObjectName("PageTitle")

        subtitle = QLabel("Loaded from /goals")
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

        self.list_layout = QVBoxLayout()
        self.list_layout.setContentsMargins(18, 18, 18, 18)
        self.list_layout.setSpacing(12)
        self.list_layout.addStretch()

        list_container = QWidget()
        list_container.setObjectName("DataList")
        list_container.setLayout(self.list_layout)

        scroll_area = QScrollArea()
        scroll_area.setObjectName("DataScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setWidget(list_container)

        page_layout.addLayout(header)
        page_layout.addWidget(self.status_label)
        page_layout.addWidget(scroll_area, 1)

    def refresh(self) -> None:
        """Load goals from the backend."""
        self._clear_list()
        self.status_label.setText("Loading goals...")

        try:
            goals = self.api_client.get_goals()
        except Exception as error:
            self.status_label.setText(f"Could not load goals: {error}")
            return

        self.status_label.setText(f"{len(goals)} goal(s)")

        if not goals:
            self._add_empty("No goals yet.")
            return

        for goal in goals:
            title = goal.get("title", "Untitled goal")
            status = goal.get("status", "unknown")
            created_at = goal.get("created_at", "")
            self._add_card(title, f"Status: {status}", created_at)

    def _clear_list(self) -> None:
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.list_layout.addStretch()

    def _add_empty(self, text: str) -> None:
        empty_container = QWidget()
        empty_layout = QVBoxLayout(empty_container)
        empty_layout.setAlignment(Qt.AlignCenter)
        
        icon_label = QLabel()
        icon = create_svg_icon(ICONS.get("EmptyState", ""), color="#4b5563")
        pixmap = icon.pixmap(48, 48)
        icon_label.setPixmap(pixmap)
        icon_label.setAlignment(Qt.AlignCenter)
        
        text_label = QLabel(text)
        text_label.setObjectName("PlaceholderText")
        text_label.setAlignment(Qt.AlignCenter)
        
        empty_layout.addStretch()
        empty_layout.addWidget(icon_label)
        empty_layout.addWidget(text_label)
        empty_layout.addStretch()
        
        stretch_item = self.list_layout.takeAt(self.list_layout.count() - 1)
        self.list_layout.addWidget(empty_container)
        if stretch_item is not None:
            self.list_layout.addItem(stretch_item)

    def _add_card(self, title: str, meta: str, detail: str) -> None:
        card = QFrame()
        card.setObjectName("DataCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(6)

        title_label = QLabel(title)
        title_label.setObjectName("BodyText")
        title_label.setWordWrap(True)
        card_layout.addWidget(title_label)

        if meta:
            meta_label = QLabel(meta)
            meta_label.setObjectName("MetaText")
            card_layout.addWidget(meta_label)

        if detail:
            detail_label = QLabel(detail)
            detail_label.setObjectName("MetaText")
            detail_label.setWordWrap(True)
            card_layout.addWidget(detail_label)

        stretch_item = self.list_layout.takeAt(self.list_layout.count() - 1)
        self.list_layout.addWidget(card)
        if stretch_item is not None:
            self.list_layout.addItem(stretch_item)
