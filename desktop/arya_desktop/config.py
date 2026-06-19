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
