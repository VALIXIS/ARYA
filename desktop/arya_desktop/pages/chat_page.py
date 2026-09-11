"""
chat_page.py
------------
Chat UI for ARYA Desktop — with push-to-talk voice support.

Voice flow:
  1. User presses-and-holds the mic button  -> recording starts
  2. User releases the mic button           -> recording stops, STT runs
  3. Transcript is sent through /chat pipeline
  4. If "Auto Read Responses" is enabled, TTS reads ARYA's reply aloud
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QIcon, QColor, QPainter, QFont
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
    QMessageBox,
)

import time

from arya_desktop.api_client import ApiClient
from arya_desktop import settings_store
from arya_desktop.voice_service import VoiceService


# ---------------------------------------------------------------------------
# Chat worker
# ---------------------------------------------------------------------------

class ChatWorker(QThread):
    """Background worker for sending chat messages to the backend."""

    reply_ready = Signal(str)
    error_ready = Signal(str)

    def __init__(self, api_client: ApiClient, message: str, debug_logs: bool = False):
        super().__init__()
        self.api_client = api_client
        self.message = message
        self._debug = debug_logs

    def run(self) -> None:
        try:
            t0 = time.time()
            reply = self.api_client.send_chat_message(self.message)
            t1 = time.time()
            if self._debug:
                print(f"[VOICE] Chat: {(t1 - t0) * 1000:.0f} ms")
            self.reply_ready.emit(reply or "ARYA returned an empty response.")
        except Exception as error:
            self.error_ready.emit(f"Could not reach ARYA backend: {error}")


# ---------------------------------------------------------------------------
# Mic button
# ---------------------------------------------------------------------------

class MicButton(QPushButton):
    """
    A hold-to-record microphone button.
    Emits pressed / released — ChatPage handles the actual recording.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MicButton")
        self.setToolTip("Hold to speak")
        self.setFixedSize(46, 46)
        self.setCursor(Qt.PointingHandCursor)
        self._active = False
        self._set_icon(active=False)

    def _set_icon(self, active: bool) -> None:
        self._active = active
        self.update()   # triggers paintEvent

    def set_active(self, active: bool) -> None:
        self._set_icon(active)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # Draw a simple microphone symbol in text
        painter.setPen(QColor("#5B8CFF" if self._active else "#ffffff"))
        font = QFont("Segoe UI", 16)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, "\U0001F3A4")   # 🎤
        painter.end()

    def set_recording_state(self, state: str) -> None:
        """Update appearance based on VoiceService state."""
        if state == "recording":
            self.set_active(True)
            self.setToolTip("Release to stop")
        elif state == "transcribing":
            self.setToolTip("Transcribing...")
        else:
            self.set_active(False)
            self.setToolTip("Hold to speak")


# ---------------------------------------------------------------------------
# Chat page
# ---------------------------------------------------------------------------

class ChatPage(QWidget):
    """Chat page connected to POST /chat, with push-to-talk voice."""

    def __init__(self, api_client: ApiClient | None = None):
        super().__init__()
        self.api_client = api_client or ApiClient()
        self.worker: ChatWorker | None = None
        self.typing_bubble: QFrame | None = None

        self.history_layout: QVBoxLayout
        self.message_input: QLineEdit
        self.send_button: QPushButton
        self.mic_button: MicButton

        # Voice service
        self._voice = VoiceService(self)
        self._voice.transcript_ready.connect(self._on_voice_transcript)
        self._voice.error_occurred.connect(self._on_voice_error)
        self._voice.state_changed.connect(self._on_voice_state)

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(36, 32, 36, 28)
        page_layout.setSpacing(18)

        title = QLabel("Chat")
        title.setObjectName("PageTitle")

        subtitle = QLabel("Talk to ARYA through the FastAPI backend on localhost:8000.")
        subtitle.setObjectName("PageSubtitle")

        # ---- Chat history area ----
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
        self._scroll_area = scroll_area

        # ---- Input row ----
        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        self.message_input = QLineEdit()
        self.message_input.setObjectName("MessageInput")
        self.message_input.setPlaceholderText("Message ARYA...")
        self.message_input.returnPressed.connect(self.send_message)

        self.send_button = QPushButton("Send")
        self.send_button.setObjectName("SendButton")
        self.send_button.clicked.connect(self.send_message)

        self.mic_button = MicButton()
        self.mic_button.pressed.connect(self._mic_pressed)
        self.mic_button.released.connect(self._mic_released)

        self.stop_button = QPushButton("Stop")
        self.stop_button.setObjectName("StopButton")
        self.stop_button.clicked.connect(self._stop_pressed)
        self.stop_button.hide()

        input_row.addWidget(self.message_input, 1)
        input_row.addWidget(self.mic_button)
        input_row.addWidget(self.stop_button)
        input_row.addWidget(self.send_button)

        # ---- Voice status label ----
        self._voice_status = QLabel("")
        self._voice_status.setObjectName("VoiceStatus")
        self._voice_status.setAlignment(Qt.AlignCenter)
        self._voice_status.hide()

        page_layout.addWidget(title)
        page_layout.addWidget(subtitle)
        page_layout.addWidget(scroll_area, 1)
        page_layout.addWidget(self._voice_status)
        page_layout.addLayout(input_row)

    # ------------------------------------------------------------------
    # Text chat
    # ------------------------------------------------------------------

    def send_message(self) -> None:
        message = self.message_input.text().strip()
        if not message or self.worker is not None:
            return
        self.message_input.clear()
        self._dispatch_message(message)

    def _dispatch_message(self, message: str, from_voice: bool = False) -> None:
        """Send a message (typed or transcribed) to the backend."""
        self._add_message("user", message, voice=from_voice)
        self._set_waiting(True)

        settings = settings_store.load_settings()
        debug_logs = settings.get("voice_debug_logs", False)

        self.worker = ChatWorker(self.api_client, message, debug_logs)
        self.worker.reply_ready.connect(lambda r: self._handle_reply(r, from_voice=from_voice))
        self.worker.error_ready.connect(self._handle_error)
        self.worker.finished.connect(self._worker_finished)
        self.worker.start()

    def _handle_reply(self, reply: str, from_voice: bool = False) -> None:
        self._add_message("assistant", reply)
        print("[CHAT] Response received")

        # Auto-read if voice was used OR the setting is enabled
        settings = settings_store.load_settings()
        if from_voice or settings.get("voice_auto_read", False):
            self._voice.speak(reply)

    def _handle_error(self, error: str) -> None:
        self._add_message("assistant", error)

    def _worker_finished(self) -> None:
        self._set_waiting(False)
        self.worker = None

    # ------------------------------------------------------------------
    # Voice / mic button
    # ------------------------------------------------------------------

    def _mic_pressed(self) -> None:
        """Start recording when mic button is pressed."""
        print("[MIC] Pressed")
        settings = settings_store.load_settings()
        if not settings.get("voice_enabled", True):
            self._show_voice_status("Voice is disabled in Settings.")
            return
        self._voice.start_recording()

    def _mic_released(self) -> None:
        """Stop recording when mic button is released."""
        if self._voice.state == "recording":
            self._voice.stop_recording()

    def _stop_pressed(self) -> None:
        """Stop ARYA speaking."""
        self._voice.stop_speaking()

    def _on_voice_transcript(self, text: str) -> None:
        """Received transcript from STT — pre-fill and dispatch."""
        self._hide_voice_status()
        safe_text = text.encode("unicode_escape").decode("utf-8")
        print(f"[STT] Transcript: \"{safe_text}\"")
        if not text.strip():
            self._show_voice_status("Could not hear anything. Try again.")
            return
        # Show transcript in the input briefly then send
        self.message_input.setText(text)
        print("[CHAT] Sending transcript")
        self._dispatch_message(text, from_voice=True)
        self.message_input.clear()

    def _on_voice_error(self, error: str) -> None:
        print(f"Voice error: {error}")
        self._show_voice_status(f"Voice error: {error}")
        QMessageBox.warning(self, "Voice Error", str(error))
        self.mic_button.set_recording_state("idle")

    def _on_voice_state(self, state: str) -> None:
        self.mic_button.set_recording_state(state)
        
        if state == "speaking":
            self.stop_button.show()
            self._show_voice_status("ARYA is speaking...")
        else:
            self.stop_button.hide()
            
        if state == "recording":
            self._show_voice_status("Listening...")
        elif state == "transcribing":
            self._show_voice_status("Transcribing...")
        elif state != "speaking":
            self._hide_voice_status()

    def _show_voice_status(self, text: str) -> None:
        self._voice_status.setText(text)
        self._voice_status.show()

    def _hide_voice_status(self) -> None:
        self._voice_status.hide()
        self._voice_status.setText("")

    # ------------------------------------------------------------------
    # Waiting state
    # ------------------------------------------------------------------

    def _set_waiting(self, waiting: bool) -> None:
        self.message_input.setDisabled(waiting)
        self.send_button.setDisabled(waiting)
        self.send_button.setText("Sending..." if waiting else "Send")

        if waiting and not self.typing_bubble:
            self.typing_bubble = self._create_bubble("assistant", "ARYA is typing...", "")
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(self.typing_bubble)
            row.addStretch()

            stretch_item = self.history_layout.takeAt(self.history_layout.count() - 1)
            self.history_layout.addLayout(row)
            if stretch_item is not None:
                self.history_layout.addItem(stretch_item)

        elif not waiting and self.typing_bubble:
            for i in range(self.history_layout.count()):
                item = self.history_layout.itemAt(i)
                if item and item.layout():
                    for j in range(item.layout().count()):
                        widget = item.layout().itemAt(j).widget()
                        if widget == self.typing_bubble:
                            layout_to_remove = item.layout()
                            while layout_to_remove.count():
                                child = layout_to_remove.takeAt(0)
                                if child.widget():
                                    child.widget().deleteLater()
                            self.history_layout.removeItem(layout_to_remove)
                            self.typing_bubble = None
                            return

    # ------------------------------------------------------------------
    # Bubble helpers
    # ------------------------------------------------------------------

    def _create_bubble(self, role: str, content: str, timestamp: str,
                       voice: bool = False) -> QFrame:
        bubble = QFrame()
        name = "UserBubble" if role == "user" else "AssistantBubble"
        if voice and role == "user":
            name = "UserVoiceBubble"
        bubble.setObjectName(name)
        bubble.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Minimum)

        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(16, 12, 16, 12)
        bubble_layout.setSpacing(4)

        # Prefix voice messages with mic icon
        display = ("\U0001F3A4 " + content) if (voice and role == "user") else content

        label = QLabel(display)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setMinimumWidth(220)
        label.setMaximumWidth(620)
        bubble_layout.addWidget(label)

        if timestamp:
            time_label = QLabel(timestamp)
            time_label.setObjectName("MetaText")
            time_layout = QHBoxLayout()
            time_layout.addStretch()
            time_layout.addWidget(time_label)
            bubble_layout.addLayout(time_layout)

        return bubble

    def _add_message(self, role: str, content: str, voice: bool = False) -> None:
        timestamp = datetime.now().strftime("%I:%M %p")
        bubble = self._create_bubble(role, content, timestamp, voice=voice)

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

        # Auto-scroll to bottom
        from PySide6.QtCore import QTimer
        QTimer.singleShot(50, lambda: self._scroll_area.verticalScrollBar().setValue(
            self._scroll_area.verticalScrollBar().maximum()
        ))
