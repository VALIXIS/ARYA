import sys
import time
import wave
import numpy as np
from PySide6.QtWidgets import QApplication, QMainWindow
from arya_desktop.pages.chat_page import ChatPage
import os

os.chdir(r"c:\Users\nagas\Documents\PROJECTS\ARYA\desktop")
sys.path.insert(0, r"c:\Users\nagas\Documents\PROJECTS\ARYA\desktop")

app = QApplication(sys.argv)
window = QMainWindow()
page = ChatPage()
window.setCentralWidget(page)
window.show()

# Connect to log errors
def on_error(err):
    print(f"TEST ERROR: {err}")
page._voice.error_occurred.connect(on_error)

print("--- WAITING FOR MODEL LOAD ---")
while getattr(sys.modules["arya_desktop.voice_service"], "_GLOBAL_MODEL", None) is None:
    app.processEvents()
    time.sleep(0.1)

# Monkey-patch the recorder to return synthetic voice instead of silence
def mock_stop():
    print("[TEST] Injecting test_1.wav instead of mic silence")
    try:
        with wave.open("test_1.wav", "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            audio = np.frombuffer(frames, dtype=np.int16)
            return audio, 1500.0
    except Exception as e:
        print(f"Failed to load test_1.wav: {e}")
        return np.array([], dtype="int16"), 1500.0

page._voice._recorder.stop = mock_stop

print("--- SIMULATING MIC PRESS ---")
page.mic_button.pressed.emit()

for _ in range(15):
    app.processEvents()
    time.sleep(0.1)

print("--- SIMULATING MIC RELEASE ---")
page.mic_button.released.emit()

# Wait for STT and CHAT to finish
for _ in range(50):
    app.processEvents()
    time.sleep(0.1)

print("--- TEST COMPLETE ---")
app.quit()
