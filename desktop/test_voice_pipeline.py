import os
import sys
import time
import numpy as np
import wave
import pyttsx3
from PySide6.QtCore import QCoreApplication

# Ensure we can import from desktop
os.chdir(r"c:\Users\nagas\Documents\PROJECTS\ARYA\desktop")
sys.path.insert(0, r"c:\Users\nagas\Documents\PROJECTS\ARYA\desktop")

from arya_desktop import settings_store
from arya_desktop.voice_service import VoiceService, TranscribeWorker
from arya_desktop.api_client import ApiClient
from arya_desktop.pages.chat_page import ChatWorker

print("--- PREPARING TESTS ---")
# Enable debug logs, disable auto read
settings = settings_store.load_settings()
settings["voice_debug_logs"] = True
settings["voice_auto_read"] = False
settings_store.save_settings(settings)

app = QCoreApplication(sys.argv)

# Generate test WAVs
tests = [
    ("Hi ARYA", "test_1.wav"),
    ("Open Chrome", "test_2.wav"),
    ("Play Naa Ready song", "test_3.wav")
]

engine = pyttsx3.init()
for text, filename in tests:
    engine.save_to_file(text, filename)
engine.runAndWait()

# Start VoiceService to trigger background model load
service = VoiceService()
# Wait for model to load
while getattr(sys.modules["arya_desktop.voice_service"], "_GLOBAL_MODEL", None) is None:
    time.sleep(0.1)
    
print("\n--- RUNNING TESTS ---")
model = getattr(sys.modules["arya_desktop.voice_service"], "_GLOBAL_MODEL")

for text, filename in tests:
    print(f"\nTesting prompt: '{text}'")
    
    try:
        with wave.open(filename, "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            audio_array = np.frombuffer(frames, dtype=np.int16)
    except Exception as e:
        print(f"Error loading wave: {e}")
        continue
            
    # Mocking recording time (we'll just pretend it took 1.5s to say)
    print(f"[VOICE] Recording: 1500 ms")
    
    # 1. Transcribe
    worker = TranscribeWorker(audio_array, model, True)
    
    # Wait for completion
    transcribed_text = []
    duration_res = []
    
    def on_transcript(t, d):
        transcribed_text.append(t)
        duration_res.append(d)
        
    worker.transcript_ready.connect(on_transcript)
    worker.start()
    
    while worker.isRunning():
        app.processEvents()
        time.sleep(0.01)
        
    res_text = transcribed_text[0] if transcribed_text else "(empty)"
    stt_duration = duration_res[0] if duration_res else 0.0
    print(f"Recognized as: '{res_text}'")
    
    # 2. Chat
    api = ApiClient()
    chat_worker = ChatWorker(api, res_text, True)
    chat_worker.start()
    
    while chat_worker.isRunning():
        app.processEvents()
        time.sleep(0.01)

    total = 1500 + stt_duration + getattr(chat_worker, "_t1", 0) # Just to show it manually if needed, but it prints itself
