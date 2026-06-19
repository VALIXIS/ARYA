"""
chat_page.py
------------
Chat UI for ARYA Desktop.
"""

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
from datetime import datetime

from arya_desktop.api_client import ApiClient


class ChatWorker(QThread):
    """Background worker for sending chat messages."""

    reply_ready = Signal(str)
    error_ready = Signal(str)

    def __init__(self, api_client: ApiClient, message: str):
        super().__init__()
        self.api_client = api_client
        self.message = message

    def run(self) -> None:
        """Send the message without blocking the UI thread."""
        try:
            reply = self.api_client.send_chat_message(self.message)
            self.reply_ready.emit(reply or "ARYA returned an empty response.")
        except Exception as error:
            self.error_ready.emit(f"Could not reach ARYA backend: {error}")


class ChatPage(QWidget):
    """Chat page connected to POST /chat."""

    def __init__(self, api_client: ApiClient | None = None):
        super().__init__()
        self.api_client = api_client or ApiClient()
        self.worker: ChatWorker | None = None
        self.typing_bubble: QFrame | None = None

        self.history_layout: QVBoxLayout
        self.message_input: QLineEdit
        self.send_button: QPushButton

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the chat page layout."""
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(36, 32, 36, 28)
        page_layout.setSpacing(18)

        title = QLabel("Chat")
        title.setObjectName("PageTitle")

        subtitle = QLabel("Talk to ARYA through the FastAPI backend on localhost:8000.")
        subtitle.setObjectName("PageSubtitle")

        self.history_layout = QVBoxLayout()
        self.history_layout.setContentsMargins(18, 18, 18, 18)
        self.history_layout.setSpacing(12)
        self.history_layout.addStretch()

        history_container = QWidget()
        history_container.setObjectName("ChatHistory")
        history_container.setLayout(self.history_layout)

        scroll_area = QScrollArea()
        scroll_area.setObjectName("ChatScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setWidget(history_container)

        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        self.message_input = QLineEdit()
        self.message_input.setObjectName("MessageInput")
        self.message_input.setPlaceholderText("Message ARYA...")
        self.message_input.returnPressed.connect(self.send_message)

        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("SendButton")
        self.send_button.clicked.connect(self.send_message)

        input_row.addWidget(self.message_input, 1)
        input_row.addWidget(self.send_button)

        page_layout.addWidget(title)
        page_layout.addWidget(subtitle)
        page_layout.addWidget(scroll_area, 1)
        page_layout.addLayout(input_row)

    def send_message(self) -> None:
        """Send the current input message to ARYA."""
        message = self.message_input.text().strip()
        if not message or self.worker is not None:
            return

        self.message_input.clear()
        self._add_message("user", message)
        self._set_waiting(True)

        self.worker = ChatWorker(self.api_client, message)
        self.worker.reply_ready.connect(self._handle_reply)
        self.worker.error_ready.connect(self._handle_error)
        self.worker.finished.connect(self._worker_finished)
        self.worker.start()

    def _handle_reply(self, reply: str) -> None:
        """Show ARYA's reply."""
        self._add_message("assistant", reply)

    def _handle_error(self, error: str) -> None:
        """Show a backend error in the chat history."""
        self._add_message("assistant", error)

    def _worker_finished(self) -> None:
        """Clean up the worker after a request finishes."""
        self._set_waiting(False)
        self.worker = None

    def _set_waiting(self, waiting: bool) -> None:
        """Enable or disable input while a message is in flight."""
        self.message_input.setDisabled(waiting)
        self.send_button.setDisabled(waiting)
        self.send_button.setText("Sending..." if waiting else "Send")

        if waiting and not self.typing_bubble:
            self.typing_bubble = self._create_bubble("assistant", "ARYA is typing...", "")
            # We insert it without standard stretching logic so it's easy to remove
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(self.typing_bubble)
            row.addStretch()
            
            stretch_item = self.history_layout.takeAt(self.history_layout.count() - 1)
            self.history_layout.addLayout(row)
            if stretch_item is not None:
                self.history_layout.addItem(stretch_item)
                
        elif not waiting and self.typing_bubble:
            # Remove the typing bubble row
            for i in range(self.history_layout.count()):
                item = self.history_layout.itemAt(i)
                if item and item.layout():
                    for j in range(item.layout().count()):
                        if item.layout().itemAt(j).widget() == self.typing_bubble:
                            layout_to_remove = item.layout()
                            while layout_to_remove.count():
                                child = layout_to_remove.takeAt(0)
                                if child.widget():
                                    child.widget().deleteLater()
                            self.history_layout.removeItem(layout_to_remove)
                            self.typing_bubble = None
                            return

    def _create_bubble(self, role: str, content: str, timestamp: str) -> QFrame:
        bubble = QFrame()
        bubble.setObjectName("UserBubble" if role == "user" else "AssistantBubble")
        bubble.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Minimum)

        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(16, 12, 16, 12)
        bubble_layout.setSpacing(4)

        label = QLabel(content)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse) if hasattr(Qt, 'TextSelectableByMouse') else label.setTextInteractionFlags(label.textInteractionFlags())
        label.setMinimumWidth(220)
        label.setMaximumWidth(620)
        bubble_layout.addWidget(label)

        if timestamp:
            time_label = QLabel(timestamp)
            time_label.setObjectName("MetaText")
            # Align time to right
            time_layout = QHBoxLayout()
            time_layout.addStretch()
            time_layout.addWidget(time_label)
            bubble_layout.addLayout(time_layout)

        return bubble

    def _add_message(self, role: str, content: str) -> None:
        """Add one message bubble to the chat history."""
        timestamp = datetime.now().strftime("%I:%M %p")
        bubble = self._create_bubble(role, content, timestamp)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)

        if role == "user":
            row.addStretch()
            row.addWidget(bubble)
        else:
            row.addWidget(bubble)
            row.addStretch()

        stretch_item = self.history_layout.takeAt(self.history_layout.count() - 1)
        self.history_layout.addLayout(row)
        if stretch_item is not None:
            self.history_layout.addItem(stretch_item)
