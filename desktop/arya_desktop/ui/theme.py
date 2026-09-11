"""
theme.py
--------
Dark theme stylesheet for ARYA Desktop.
"""


def dark_theme() -> str:
    """Return the application stylesheet."""
    return """
    QWidget {
        background: #111214;
        color: #f4f4f5;
        font-family: "Segoe UI", Arial, sans-serif;
        font-size: 14px;
    }

    QMainWindow {
        background: #111214;
    }

    #Sidebar {
        background: #18191c;
        border-right: 1px solid #2a2b30;
    }

    #AppTitle {
        color: #f4f4f5;
        font-size: 20px;
        font-weight: 700;
        padding: 18px 18px 10px 18px;
    }

    #NavButton {
        background: transparent;
        color: #a3a6ae;
        border: none;
        border-radius: 8px;
        padding: 10px 14px;
        text-align: left;
        font-weight: 600;
        font-size: 14px;
    }

    #NavButton:hover {
        background: #24262b;
        color: #ffffff;
    }

    #NavButton[active="true"] {
        background: #303238;
        color: #ffffff;
    }

    #ContentArea {
        background: #111214;
    }

    #PageTitle {
        color: #ffffff;
        font-size: 28px;
        font-weight: 700;
    }

    #PageSubtitle {
        color: #a3a6ae;
        font-size: 14px;
    }

    #PlaceholderPanel {
        background: #18191c;
        border: 1px solid #2a2b30;
        border-radius: 8px;
    }

    #ChatScrollArea {
        background: #111214;
        border: 1px solid #2a2b30;
        border-radius: 8px;
    }

    #ChatHistory {
        background: #111214;
    }

    #MessageInput {
        background: #18191c;
        color: #ffffff;
        border: 1px solid #303238;
        border-radius: 8px;
        padding: 12px 14px;
        selection-background-color: #3b82f6;
    }

    #MessageInput:focus {
        border: 1px solid #4b5563;
    }

    #SendButton {
        background: #f4f4f5;
        color: #111214;
        border: none;
        border-radius: 8px;
        padding: 12px 18px;
        font-weight: 700;
    }

    #SendButton:hover {
        background: #ffffff;
    }

    #SendButton:disabled {
        background: #3a3c42;
        color: #a3a6ae;
    }

    #UserBubble {
        background: #2f3138;
        border-radius: 12px;
        border-bottom-right-radius: 4px;
    }

    #AssistantBubble {
        background: #18191c;
        border: 1px solid #2a2b30;
        border-radius: 12px;
        border-bottom-left-radius: 4px;
    }

    #RefreshButton {
        background: #24262b;
        color: #ffffff;
        border: 1px solid #303238;
        border-radius: 8px;
        padding: 10px 14px;
        font-weight: 600;
    }

    #RefreshButton:hover {
        background: #303238;
    }

    #DataScrollArea {
        background: #111214;
        border: 1px solid #2a2b30;
        border-radius: 8px;
    }

    #DataList {
        background: #111214;
    }

    #DataCard {
        background: #18191c;
        border: 1px solid #2a2b30;
        border-radius: 8px;
    }

    #BodyText {
        color: #f4f4f5;
        font-size: 14px;
    }

    #MetaText {
        color: #a3a6ae;
        font-size: 12px;
    }

    #PlaceholderTitle {
        color: #ffffff;
        font-size: 18px;
        font-weight: 600;
        margin-top: 10px;
    }

    #PlaceholderText {
        color: #a3a6ae;
        font-size: 14px;
    }

    #SettingsCheckbox {
        color: #f4f4f5;
        spacing: 10px;
    }

    #SettingsCheckbox::indicator {
        width: 18px;
        height: 18px;
        border: 1px solid #4b5563;
        border-radius: 4px;
        background: #18191c;
    }

    #SettingsCheckbox::indicator:checked {
        background: #5B8CFF;
        border: 1px solid #5B8CFF;
    }

    #SettingsCheckbox:disabled {
        color: #6b7280;
    }

    #MicButton {
        background: #1e2028;
        border: 1.5px solid #303238;
        border-radius: 8px;
        padding: 0px;
        font-size: 18px;
    }

    #MicButton:hover {
        background: #24262b;
        border-color: #5B8CFF;
    }

    #MicButton:pressed {
        background: #1a2a4a;
        border-color: #5B8CFF;
    }

    #UserVoiceBubble {
        background: #1a2a4a;
        border: 1.5px solid #5B8CFF;
        border-radius: 12px;
        border-bottom-right-radius: 4px;
    }

    #VoiceStatus {
        color: #5B8CFF;
        font-size: 13px;
        padding: 4px 0px;
    }
    """
