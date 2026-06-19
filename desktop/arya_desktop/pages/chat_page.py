"""
chat_page.py
------------
Chat UI for ARYA Desktop.
"""

from PySide6.QtCore import QThread, Signal
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

    def _add_message(self, role: str, content: str) -> None:
        """Add one message bubble to the chat history."""
        bubble = QFrame()
        bubble.setObjectName("UserBubble" if role == "user" else "AssistantBubble")
        bubble.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Minimum)

        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(14, 10, 14, 10)

        label = QLabel(content)
        label.setWordWrap(True)
        label.setTextInteractionFlags(label.textInteractionFlags())
        label.setMinimumWidth(220)
        label.setMaximumWidth(620)
        bubble_layout.addWidget(label)

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
