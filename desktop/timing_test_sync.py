import os, sys, time, wave, tempfile
os.environ["PYTHONUTF8"] = "1"
import numpy as np
import requests
from faster_whisper import WhisperModel
import requests
from faster_whisper import WhisperModel

print("--- INITIALIZING MODEL ---")
t0 = time.time()
model_path = os.path.join(os.path.dirname(__file__), "whisper_model_tmp")
model = WhisperModel("tiny", device="cpu", compute_type="int8", download_root=model_path)
t1 = time.time()
print(f"[VOICE] Model: tiny")
print(f"[VOICE] Loaded in {int((t1-t0)*1000)} ms")

# Generate 1.5 seconds of simulated audio (random noise to avoid empty trim)
np.random.seed(42)
audio = np.random.randint(-1000, 1000, 16000 * 2, dtype=np.int16)

tests = [
    "Hi ARYA",
    "Open Chrome",
    "Play Naa Ready song"
]

for text in tests:
    print(f"\n--- Testing: {text} ---")
    print("[VOICE] Recording: 1500 ms")
    
    # STT Time (Using the 1.5s audio array)
    t_stt0 = time.time()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    with wave.open(tmp_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(audio.tobytes())
        
    # We disable VAD filter for this specific benchmark since noise would be filtered out instantly,
    # and we want to see the real inference time over 1.5s of audio.
    segments, _ = model.transcribe(tmp_path, beam_size=5, vad_filter=False)
    list(segments) # force evaluation
    os.unlink(tmp_path)
    t_stt1 = time.time()
    
    stt_ms = int((t_stt1 - t_stt0) * 1000)
    print(f"[VOICE] STT: {stt_ms} ms (Simulated Inference)")
    
    # Chat Time (using the actual text)
    t_chat0 = time.time()
    try:
        r = requests.post("http://localhost:8000/chat", json={"message": text}, timeout=15)
        r.raise_for_status()
    except Exception as e:
        print(f"Backend error: {e}")
    t_chat1 = time.time()
    chat_ms = int((t_chat1 - t_chat0) * 1000)
    print(f"[VOICE] Chat: {chat_ms} ms")
    
    total = stt_ms + chat_ms
    print(f"Total time from speech end to ARYA reply: {total} ms")
