"""
settings_page.py
----------------
Settings page for ARYA Desktop.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from arya_desktop import notification_service, settings_store, startup_manager


class SettingsPage(QWidget):
    """Local desktop settings, including Windows auto-start and notifications."""

    def __init__(self):
        super().__init__()
        self.startup_checkbox: QCheckBox
        self.notifications_checkbox: QCheckBox
        self.daily_briefing_checkbox: QCheckBox
        self.voice_checkbox: QCheckBox
        self.auto_read_checkbox: QCheckBox
        self.debug_logs_checkbox: QCheckBox
        self.response_length_combo: QComboBox
        self.tts_engine_combo: QComboBox
        self.status_label: QLabel
        self._updating = False
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(36, 32, 36, 28)
        page_layout.setSpacing(18)

        title = QLabel("Settings")
        title.setObjectName("PageTitle")

        subtitle = QLabel("Configure ARYA Desktop on this computer.")
        subtitle.setObjectName("PageSubtitle")

        startup_panel = QFrame()
        startup_panel.setObjectName("DataCard")
        startup_layout = QVBoxLayout(startup_panel)
        startup_layout.setContentsMargins(18, 18, 18, 18)
        startup_layout.setSpacing(12)

        startup_row = QHBoxLayout()
        startup_row.setSpacing(12)

        self.startup_checkbox = QCheckBox("Launch ARYA when Windows starts")
        self.startup_checkbox.setObjectName("SettingsCheckbox")
        self.startup_checkbox.setCursor(Qt.PointingHandCursor)
        self.startup_checkbox.toggled.connect(self._handle_startup_toggle)

        startup_row.addWidget(self.startup_checkbox)
        startup_row.addStretch()
        startup_layout.addLayout(startup_row)

        notifications_panel = QFrame()
        notifications_panel.setObjectName("DataCard")
        notifications_layout = QVBoxLayout(notifications_panel)
        notifications_layout.setContentsMargins(18, 18, 18, 18)
        notifications_layout.setSpacing(12)

        notifications_row = QHBoxLayout()
        notifications_row.setSpacing(12)

        self.notifications_checkbox = QCheckBox("Enable Notifications")
        self.notifications_checkbox.setObjectName("SettingsCheckbox")
        self.notifications_checkbox.setCursor(Qt.PointingHandCursor)
        self.notifications_checkbox.toggled.connect(self._handle_notifications_toggle)

        notifications_row.addWidget(self.notifications_checkbox)
        notifications_row.addStretch()
        notifications_layout.addLayout(notifications_row)

        briefing_row = QHBoxLayout()
        briefing_row.setSpacing(12)

        self.daily_briefing_checkbox = QCheckBox("Enable Daily Briefing")
        self.daily_briefing_checkbox.setObjectName("SettingsCheckbox")
        self.daily_briefing_checkbox.setCursor(Qt.PointingHandCursor)
        self.daily_briefing_checkbox.toggled.connect(self._handle_daily_briefing_toggle)

        briefing_row.addWidget(self.daily_briefing_checkbox)
        briefing_row.addStretch()
        notifications_layout.addLayout(briefing_row)

        self.status_label = QLabel("")
        self.status_label.setObjectName("PageSubtitle")
        self.status_label.setWordWrap(True)

        # ---- Voice panel ----
        voice_panel = QFrame()
        voice_panel.setObjectName("DataCard")
        voice_layout = QVBoxLayout(voice_panel)
        voice_layout.setContentsMargins(18, 18, 18, 18)
        voice_layout.setSpacing(12)

        voice_title = QLabel("Voice")
        voice_title.setObjectName("PlaceholderTitle")
        voice_layout.addWidget(voice_title)

        voice_row = QHBoxLayout()
        voice_row.setSpacing(12)
        self.voice_checkbox = QCheckBox("Enable Voice (Push-to-Talk)")
        self.voice_checkbox.setObjectName("SettingsCheckbox")
        self.voice_checkbox.setCursor(Qt.PointingHandCursor)
        self.voice_checkbox.toggled.connect(self._handle_voice_toggle)
        voice_row.addWidget(self.voice_checkbox)
        voice_row.addStretch()
        voice_layout.addLayout(voice_row)

        auto_read_row = QHBoxLayout()
        auto_read_row.setSpacing(12)
        self.auto_read_checkbox = QCheckBox("Auto Read Responses Aloud")
        self.auto_read_checkbox.setObjectName("SettingsCheckbox")
        self.auto_read_checkbox.setCursor(Qt.PointingHandCursor)
        self.auto_read_checkbox.toggled.connect(self._handle_auto_read_toggle)
        auto_read_row.addWidget(self.auto_read_checkbox)
        auto_read_row.addStretch()
        voice_layout.addLayout(auto_read_row)

        debug_logs_row = QHBoxLayout()
        debug_logs_row.setSpacing(12)
        self.debug_logs_checkbox = QCheckBox("Enable Voice Debug Logs")
        self.debug_logs_checkbox.setObjectName("SettingsCheckbox")
        self.debug_logs_checkbox.setCursor(Qt.PointingHandCursor)
        self.debug_logs_checkbox.toggled.connect(self._handle_debug_logs_toggle)
        debug_logs_row.addWidget(self.debug_logs_checkbox)
        debug_logs_row.addStretch()
        voice_layout.addLayout(debug_logs_row)

        response_length_row = QHBoxLayout()
        response_length_row.setSpacing(12)
        response_length_label = QLabel("Response Length:")
        response_length_label.setObjectName("SettingsLabel")
        self.response_length_combo = QComboBox()
        self.response_length_combo.addItems(["Brief", "Normal", "Detailed"])
        self.response_length_combo.currentTextChanged.connect(self._handle_response_length_change)
        response_length_row.addWidget(response_length_label)
        response_length_row.addWidget(self.response_length_combo)
        response_length_row.addStretch()
        voice_layout.addLayout(response_length_row)

        tts_engine_row = QHBoxLayout()
        tts_engine_row.setSpacing(12)
        tts_engine_label = QLabel("TTS Engine:")
        tts_engine_label.setObjectName("SettingsLabel")
        self.tts_engine_combo = QComboBox()
        self.tts_engine_combo.addItems(["PowerShell", "pyttsx3"])
        self.tts_engine_combo.currentTextChanged.connect(self._handle_tts_engine_change)
        tts_engine_row.addWidget(tts_engine_label)
        tts_engine_row.addWidget(self.tts_engine_combo)
        tts_engine_row.addStretch()
        voice_layout.addLayout(tts_engine_row)

        voice_note = QLabel("Requires: faster-whisper, sounddevice, pyttsx3")
        voice_note.setObjectName("MetaText")
        voice_layout.addWidget(voice_note)

        page_layout.addWidget(title)
        page_layout.addWidget(subtitle)
        page_layout.addWidget(startup_panel)
        page_layout.addWidget(notifications_panel)
        page_layout.addWidget(voice_panel)
        page_layout.addWidget(self.status_label)
        page_layout.addStretch()

    def refresh(self) -> None:
        """Load saved settings into the page."""
        settings = settings_store.load_settings()

        self._updating = True
        self.startup_checkbox.setChecked(settings.get("launch_on_startup", False))
        self.notifications_checkbox.setChecked(
            settings.get("enable_notifications", False)
        )
        self.daily_briefing_checkbox.setChecked(
            settings.get("enable_daily_briefing", False)
        )
        self.voice_checkbox.setChecked(settings.get("voice_enabled", True))
        self.auto_read_checkbox.setChecked(settings.get("voice_auto_read", False))
        self.debug_logs_checkbox.setChecked(settings.get("voice_debug_logs", False))
        self.response_length_combo.setCurrentText(settings.get("response_length", "Brief"))
        self.tts_engine_combo.setCurrentText(settings.get("tts_engine", "PowerShell"))
        self._updating = False

        self._sync_notification_controls()
        self._update_status_text()

    def _sync_notification_controls(self) -> None:
        """Keep notification-related controls in a valid state."""
        notifications_enabled = self.notifications_checkbox.isChecked()
        self.daily_briefing_checkbox.setEnabled(notifications_enabled)

        if not notification_service.is_windows():
            self.notifications_checkbox.setEnabled(False)
            self.daily_briefing_checkbox.setEnabled(False)

        if not startup_manager.is_windows():
            self.startup_checkbox.setEnabled(False)

    def _update_status_text(self) -> None:
        """Show the settings file path and platform notes."""
        settings_path = settings_store.get_settings_path()
        lines = [f"Settings file: {settings_path}"]

        if startup_manager.is_windows():
            lines.append(f"Startup shortcut: {startup_manager.get_shortcut_path()}")
        else:
            lines.append("Auto-start is only available on Windows.")

        if not notification_service.is_windows():
            lines.append("Notifications are only available on Windows.")

        self.status_label.setText("\n".join(lines))

    def _handle_startup_toggle(self, enabled: bool) -> None:
        """Enable or disable Windows startup when the checkbox changes."""
        if self._updating:
            return

        if not startup_manager.is_windows():
            return

        settings = settings_store.load_settings()
        settings["launch_on_startup"] = enabled

        try:
            if enabled:
                startup_manager.enable_startup()
            else:
                startup_manager.disable_startup()
        except Exception as error:
            self._updating = True
            self.startup_checkbox.setChecked(not enabled)
            self._updating = False
            self.status_label.setText(f"Could not update startup setting: {error}")
            return

        settings_store.save_settings(settings)
        self._update_status_text()

    def _handle_notifications_toggle(self, enabled: bool) -> None:
        """Save the notifications master switch."""
        if self._updating:
            return

        settings = settings_store.load_settings()
        settings["enable_notifications"] = enabled

        if not enabled:
            settings["enable_daily_briefing"] = False
            self._updating = True
            self.daily_briefing_checkbox.setChecked(False)
            self._updating = False

        settings_store.save_settings(settings)
        self._sync_notification_controls()
        self._update_status_text()

    def _handle_daily_briefing_toggle(self, enabled: bool) -> None:
        """Save the daily briefing notification setting."""
        if self._updating:
            return

        if not self.notifications_checkbox.isChecked():
            return

        settings = settings_store.load_settings()
        settings["enable_daily_briefing"] = enabled
        settings_store.save_settings(settings)
        self._update_status_text()

    def _handle_voice_toggle(self, enabled: bool) -> None:
        """Save the voice enabled setting."""
        if self._updating:
            return
        settings = settings_store.load_settings()
        settings["voice_enabled"] = enabled
        settings_store.save_settings(settings)

    def _handle_auto_read_toggle(self, enabled: bool) -> None:
        """Save the auto-read responses setting."""
        if self._updating:
            return
        settings = settings_store.load_settings()
        settings["voice_auto_read"] = enabled
        settings_store.save_settings(settings)

    def _handle_debug_logs_toggle(self, enabled: bool) -> None:
        """Save the voice debug logs setting."""
        if self._updating:
            return
        settings = settings_store.load_settings()
        settings["voice_debug_logs"] = enabled
        settings_store.save_settings(settings)

    def _handle_response_length_change(self, text: str) -> None:
        """Save the response length setting."""
        if self._updating:
            return
        settings = settings_store.load_settings()
        settings["response_length"] = text
        settings_store.save_settings(settings)

    def _handle_tts_engine_change(self, text: str) -> None:
        """Save the TTS engine setting."""
        if self._updating:
            return
        settings = settings_store.load_settings()
        settings["tts_engine"] = text
        settings_store.save_settings(settings)
