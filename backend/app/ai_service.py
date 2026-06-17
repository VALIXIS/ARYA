"""
ai_service.py
--------------
Handles all communication with the local Ollama server running the
qwen3:8b model. This keeps AI-specific code isolated from the rest
of the app, so the model or provider can be changed later without
touching the API routes.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")


def ask_ai(message: str) -> str:
    """
    Send a message to the local Ollama model and return its text reply.

    Requires Ollama to be running locally with the qwen3:8b model pulled,
    e.g. via: `ollama run qwen3:8b`
    """
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": message,
        "stream": False,
    }

    response = requests.post(url, json=payload, timeout=120)
    response.raise_for_status()

    data = response.json()
    return data.get("response", "").strip()
