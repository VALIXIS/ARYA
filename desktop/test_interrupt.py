import sys
import time
from PySide6.QtWidgets import QApplication, QMainWindow
from arya_desktop.pages.chat_page import ChatPage
import os

os.chdir(r"c:\Users\nagas\Documents\PROJECTS\ARYA\desktop")
sys.path.insert(0, r"c:\Users\nagas\Documents\PROJECTS\ARYA\desktop")

app = QApplication(sys.argv)
window = QMainWindow()

class MockApiClient:
    def __init__(self):
        self.call_count = 0
        
    def send_chat_message(self, message: str) -> str:
        self.call_count += 1
        print(f"[MOCK API] Received: {message}")
        return f"This is response number {self.call_count}. " * 3

api = MockApiClient()
page = ChatPage(api_client=api)
window.setCentralWidget(page)
window.show()

# Force voice enabled, Auto Read ON, PowerShell
from arya_desktop import settings_store
s = settings_store.load_settings()
s["voice_enabled"] = True
s["voice_auto_read"] = True
s["tts_engine"] = "PowerShell"
settings_store.save_settings(s)

def process_events(secs):
    for _ in range(int(secs * 10)):
        app.processEvents()
        time.sleep(0.1)

print("--- WAITING FOR MODEL LOAD ---")
while getattr(sys.modules["arya_desktop.voice_service"], "_GLOBAL_MODEL", None) is None:
    process_events(0.1)

print("\n--- TEST: 5 QUESTIONS ---")
for i in range(1, 6):
    print(f"\nQuestion {i}...")
    page._dispatch_message(f"Question {i}", from_voice=False)
    process_events(1.0)
    
    # Test interrupt randomly
    if i == 3:
        print("[TEST] Pressing Stop button")
        page.stop_button.clicked.emit()
    elif i == 5:
        print("[TEST] Voice interrupt 'Stop'")
        page._voice._on_transcript("stop", 500)
    else:
        # Just wait for TTS to finish naturally
        while page._voice.state == "speaking":
            process_events(0.1)

print(f"\n--- API Call Count: {api.call_count} ---")
print("--- TEST COMPLETE ---")
app.quit()
