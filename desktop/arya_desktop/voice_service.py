"""
voice_service.py
----------------
Push-to-talk voice pipeline for ARYA Desktop.

Responsibilities:
  1. Record audio while the mic button is held (sounddevice)
  2. Transcribe with faster-whisper (local, tiny model by default)
  3. Read replies aloud with Windows SAPI via pyttsx3 / subprocess
  4. Expose a VoiceService singleton used by ChatPage

All work runs in QThread workers so the UI never blocks.
"""

from __future__ import annotations

import io
import sys
import wave
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable

import numpy as np
from PySide6.QtCore import QThread, Signal, QObject

from arya_desktop import settings_store


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SAMPLE_RATE  = 16_000    # Hz — Whisper expects 16 kHz
CHANNELS     = 1
DTYPE        = "int16"
WHISPER_MODEL = "tiny"   # tiny / base / small — trades speed vs accuracy

# Global model cache to ensure it's loaded only once for the app lifetime
_GLOBAL_MODEL = None


# ---------------------------------------------------------------------------
# Audio recorder (runs in a background thread, not a QThread)
# ---------------------------------------------------------------------------

class _AudioRecorder:
    """Synchronous recorder that collects chunks while recording=True."""

    def __init__(self) -> None:
        self._chunks: list[np.ndarray] = []
        self._recording = False
        self._lock = threading.Lock()
        self._t0 = 0.0

    def start(self) -> None:
        import sounddevice as sd  # lazy import — only needed when voice is used

        self._chunks.clear()
        self._recording = True
        self._t0 = time.time()
        # print("[VOICE] Recording started") # removed per requirements focus

        def _callback(indata, frames, time, status):
            if self._recording:
                with self._lock:
                    self._chunks.append(indata.copy())

        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            callback=_callback,
        )
        self._stream.start()

    def stop(self) -> tuple[np.ndarray, float]:
        self._recording = False
        self._stream.stop()
        self._stream.close()
        duration = (time.time() - self._t0) * 1000

        with self._lock:
            if not self._chunks:
                return np.array([], dtype=DTYPE), duration
            return np.concatenate(self._chunks, axis=0), duration


# ---------------------------------------------------------------------------
# Transcription worker
# ---------------------------------------------------------------------------

class TranscribeWorker(QThread):
    """Transcribes audio bytes in a background thread."""

    transcript_ready = Signal(str, float)
    error_occurred   = Signal(str)

    def __init__(self, audio: np.ndarray, model, debug_logs: bool):
        super().__init__()
        self._audio = audio
        self._model = model
        self._debug = debug_logs

    def run(self) -> None:
        if self._model is None:
            self.error_occurred.emit("Model is still loading...")
            return

        try:
            print("[STT] Transcription started")
            t0 = time.time()
            if self._audio.size == 0:
                self.error_occurred.emit("No audio captured.")
                return

            # Save to a temp WAV so faster-whisper can read it
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name

            with wave.open(tmp_path, "wb") as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(2)           # int16 = 2 bytes
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(self._audio.tobytes())

            # vad_filter=True to trim silence
            segments, info = self._model.transcribe(tmp_path, beam_size=5, vad_filter=True)
            transcript = " ".join(seg.text.strip() for seg in segments).strip()

            Path(tmp_path).unlink(missing_ok=True)

            t1 = time.time()
            duration_ms = (t1 - t0) * 1000

            if self._debug:
                print(f"[VOICE] STT: {duration_ms:.0f} ms")

            print("[STT] Transcription finished")
            self.transcript_ready.emit(transcript, duration_ms)

        except Exception as exc:
            self.error_occurred.emit(str(exc))


# ---------------------------------------------------------------------------
# TTS worker
# ---------------------------------------------------------------------------

class TtsWorker(QThread):
    """Speaks text aloud using Windows SAPI (via pyttsx3 or PowerShell)."""

    finished = Signal()

    def __init__(self, text: str, debug_logs: bool, engine_choice: str):
        super().__init__()
        self._text = text
        self._debug = debug_logs
        self._engine_choice = engine_choice
        self._process = None
        self._stopped = False

    def stop(self) -> None:
        self._stopped = True
        if self._process:
            try:
                self._process.kill()
            except Exception:
                pass

    def run(self) -> None:
        if self._stopped:
            return
        t0 = time.time()
        print("[TTS] Started")
        try:
            if self._engine_choice == "PowerShell":
                self._speak_powershell(self._text)
            else:
                self._speak_pyttsx3(self._text)
        except Exception as exc:
            # Fallback if primary fails
            try:
                if self._engine_choice == "PowerShell":
                    self._speak_pyttsx3(self._text)
                else:
                    self._speak_powershell(self._text)
            except Exception:
                pass

        t1 = time.time()
        duration_ms = (t1 - t0) * 1000
        
        if self._stopped:
            print("[TTS] Interrupted")
        else:
            print("[TTS] Finished")
            if self._debug:
                print(f"[TTS] {duration_ms:.0f} ms")
            
        self.finished.emit()

    def _speak_pyttsx3(self, text: str) -> None:
        import pyttsx3  # type: ignore
        engine = pyttsx3.init()
        engine.setProperty("rate", 180)   # words per minute
        engine.setProperty("volume", 1.0)
        engine.say(text)
        engine.runAndWait()

    def _speak_powershell(self, text: str) -> None:
        import subprocess
        safe = text.replace("'", "''")
        ps = f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{safe}')"
        self._process = subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-NoProfile", "-Command", ps],
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        self._process.wait()


# ---------------------------------------------------------------------------
# VoiceService — owned by ChatPage
# ---------------------------------------------------------------------------

class VoiceService(QObject):
    """
    Coordinates push-to-talk recording, transcription and TTS.

    Signals
    -------
    transcript_ready(str)   — emitted when STT finishes; caller should send to /chat
    tts_finished()          — emitted when audio playback ends
    error_occurred(str)     — emitted on any failure
    state_changed(str)      — 'idle' | 'recording' | 'transcribing' | 'speaking'
    """

    transcript_ready = Signal(str)
    tts_finished     = Signal()
    error_occurred   = Signal(str)
    state_changed    = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._recorder   = _AudioRecorder()
        self._transcribe_worker: TranscribeWorker | None = None
        self._tts_worker: TtsWorker | None = None
        self._state = "idle"
        
        # Start background load of the model
        threading.Thread(target=self._load_model_bg, daemon=True).start()

    def _load_model_bg(self) -> None:
        global _GLOBAL_MODEL
        if _GLOBAL_MODEL is not None:
            return  # Already loaded
        
        t0 = time.time()
        try:
            import os
            os.environ["PYTHONUTF8"] = "1"
            from faster_whisper import WhisperModel
            model_dir = os.path.join(os.path.dirname(__file__), "whisper_model_tmp")
            _GLOBAL_MODEL = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8", download_root=model_dir)
            t1 = time.time()
            duration_ms = (t1 - t0) * 1000
            print(f"[VOICE] Model: {WHISPER_MODEL}")
            print(f"[VOICE] Loaded in {int(duration_ms)} ms")
        except Exception as e:
            print(f"[VOICE] Failed to load model: {e}")

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def start_recording(self) -> None:
        if self._state not in ("idle", "speaking"):
            return
        self._set_state("recording")
        print("[MIC] Recording started")
        try:
            self._recorder.start()
        except Exception as exc:
            self.error_occurred.emit(f"Microphone error: {exc}")
            self._set_state("idle")

    def stop_recording(self) -> None:
        if self._state != "recording":
            return
        self._set_state("transcribing")
        print("[MIC] Recording stopped")
        try:
            audio, rec_duration = self._recorder.stop()
        except Exception as exc:
            self.error_occurred.emit(f"Recording error: {exc}")
            self._set_state("idle")
            return

        print(f"[MIC] Audio length: {rec_duration / 1000:.2f} seconds")

        settings = settings_store.load_settings()
        debug_logs = settings.get("voice_debug_logs", False)

        if debug_logs:
            print(f"[VOICE] Recording: {rec_duration:.0f} ms")

        global _GLOBAL_MODEL
        self._transcribe_worker = TranscribeWorker(audio, _GLOBAL_MODEL, debug_logs)
        self._transcribe_worker.transcript_ready.connect(self._on_transcript)
        self._transcribe_worker.error_occurred.connect(self._on_transcribe_error)
        self._transcribe_worker.start()

    # ------------------------------------------------------------------
    # TTS
    # ------------------------------------------------------------------

    def speak(self, text: str) -> None:
        if not text.strip():
            return
        self._set_state("speaking")
        
        settings = settings_store.load_settings()
        debug_logs = settings.get("voice_debug_logs", False)
        engine_choice = settings.get("tts_engine", "PowerShell")
        
        self._tts_worker = TtsWorker(text, debug_logs, engine_choice)
        self._tts_worker.finished.connect(self._on_tts_finished)
        self._tts_worker.start()

    def stop_speaking(self) -> None:
        """Interrupt active TTS immediately."""
        if self._tts_worker:
            self._tts_worker.stop()
        print("[TTS] Stopped by user")
        self._set_state("idle")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _set_state(self, state: str) -> None:
        self._state = state
        self.state_changed.emit(state)

    def _on_transcript(self, text: str, duration_ms: float) -> None:
        self._set_state("idle")
        
        # Check for voice interrupt commands
        lower_text = text.lower().strip(".,!?;:\"'()[]{} ")
        interrupt_cmds = ["stop", "stop talking", "be quiet", "enough"]
        if lower_text in interrupt_cmds:
            self.stop_speaking()
            return  # Do not emit transcript
            
        self.transcript_ready.emit(text)

    def _on_transcribe_error(self, error: str) -> None:
        self.error_occurred.emit(error)
        self._set_state("idle")

    def _on_tts_finished(self) -> None:
        self._set_state("idle")
        self.tts_finished.emit()

    @property
    def state(self) -> str:
        return self._state
