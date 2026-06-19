"""
config.py
---------
Shared configuration for the ARYA desktop app.
"""

BACKEND_BASE_URL = "http://localhost:8000"
APP_NAME = "ARYA Desktop"

# Health-check endpoints (use 127.0.0.1 to avoid DNS/IPv6 delays on Windows)
OLLAMA_HEALTH_URL = "http://127.0.0.1:11434/api/tags"
BACKEND_HEALTH_URL = "http://127.0.0.1:8000/memory"

# Logging directory (same location as settings_store)
import os
from pathlib import Path

LOG_DIR = Path(os.environ.get("APPDATA", Path.home())) / "ARYA"
LOG_DIR.mkdir(parents=True, exist_ok=True)

ARYA_LOG = LOG_DIR / "arya.log"
BACKEND_LOG = LOG_DIR / "arya_backend.log"
OLLAMA_LOG = LOG_DIR / "arya_ollama.log"

