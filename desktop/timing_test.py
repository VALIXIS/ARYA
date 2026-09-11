import time
import numpy as np
import tempfile
import wave
import os

print("--- TIMING BREAKDOWN SCRIPT ---")

# 1. Recording (Simulated)
t0 = time.time()
time.sleep(3.0)  # simulate a 3-second recording
audio = np.zeros(16000 * 3, dtype=np.int16)
t1 = time.time()
print(f"Recording: {t1 - t0:.2f} seconds")

# 2. Transcription
t2 = time.time()
from faster_whisper import WhisperModel
with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
    tmp_path = tmp.name
with wave.open(tmp_path, "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(16000)
    wf.writeframes(audio.tobytes())

# Measure model load + transcription
t_load_start = time.time()
model = WhisperModel("tiny", device="cpu", compute_type="int8")
t_load_end = time.time()

t_trans_start = time.time()
segments, info = model.transcribe(tmp_path, beam_size=5)
transcript = " ".join(seg.text.strip() for seg in segments).strip()
t_trans_end = time.time()

os.unlink(tmp_path)
t3 = time.time()

print(f"Transcription Total: {t3 - t2:.2f} seconds")
print(f"  -> Model Load Time: {t_load_end - t_load_start:.2f} seconds")
print(f"  -> Inference Time: {t_trans_end - t_trans_start:.2f} seconds")

# 3. Chat (Simulated backend call)
t4 = time.time()
try:
    import requests
    response = requests.post("http://localhost:8000/chat", json={"message": "hello"}, timeout=5)
    response.raise_for_status()
    chat_time = time.time() - t4
    print(f"Chat (Backend API): {chat_time:.2f} seconds")
except Exception as e:
    time.sleep(0.5)
    print(f"Chat (Backend API): 0.50 seconds (simulated, backend not running)")

# 4. TTS
t5 = time.time()
import pyttsx3
engine = pyttsx3.init()
engine.setProperty("rate", 180)
engine.say("Testing text to speech.")
engine.runAndWait()
t6 = time.time()
print(f"TTS (pyttsx3): {t6 - t5:.2f} seconds")
