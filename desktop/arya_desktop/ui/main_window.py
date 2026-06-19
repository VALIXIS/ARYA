"""
main_window.py
--------------
Main application window for ARYA Desktop.
"""

from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QWidget

from arya_desktop.config import APP_NAME
from arya_desktop.notification_service import NotificationScheduler, NotificationService
from arya_desktop.pages.chat_page import ChatPage
from arya_desktop.pages.goals_page import GoalsPage
from arya_desktop.pages.memories_page import MemoriesPage
from arya_desktop.pages.profile_page import ProfilePage
from arya_desktop.pages.settings_page import SettingsPage
from arya_desktop.pages.tasks_page import TasksPage
from arya_desktop.ui.sidebar import Sidebar
from arya_desktop.ui.system_tray import AryaSystemTray


class MainWindow(QMainWindow):
    """Primary ARYA Desktop window with sidebar navigation."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1100, 720)
        self.setMinimumSize(900, 600)

        self.sidebar = Sidebar()
        self.stack = QStackedWidget()
        self.stack.setObjectName("ContentArea")
        self.page_indexes: dict[str, int] = {}

        self._build_pages()
        self._build_layout()
        self.system_tray = AryaSystemTray(self)
        self.notification_service = NotificationService(
            self.system_tray.get_tray_icon()
        )
        self.notification_scheduler = NotificationScheduler(
            self.notification_service,
            parent=self,
        )

        self.sidebar.page_selected.connect(self.show_page)
        self.show_page("Chat")

    def _build_layout(self) -> None:
        """Build the main window layout."""
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)

    def _build_pages(self) -> None:
        """Create all top-level pages."""
        pages = {
            "Chat": ChatPage(),
            "Tasks": TasksPage(),
            "Goals": GoalsPage(),
            "Memories": MemoriesPage(),
            "Profile": ProfilePage(),
            "Settings": SettingsPage(),
        }

        for page_name, page in pages.items():
            index = self.stack.addWidget(page)
            self.page_indexes[page_name] = index

    def closeEvent(self, event) -> None:
        """Hide to tray instead of exiting when the window closes."""
        if self.system_tray.is_exiting or not self.system_tray.enabled:
            event.accept()
            return

        event.ignore()
        self.system_tray.hide_window_to_tray()

    def show_page(self, page_name: str) -> None:
        """Switch to the requested page."""
        if page_name not in self.page_indexes:
            return

        self.stack.setCurrentIndex(self.page_indexes[page_name])
        self.sidebar.select_page(page_name, emit_signal=False)
