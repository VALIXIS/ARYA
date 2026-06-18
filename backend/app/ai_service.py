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


def build_prompt(message: str, memories: list[str] | None = None) -> str:
    """Build the prompt sent to Qwen, including relevant memories when available."""
    memories = memories or []
    if not memories:
        return message

    memory_text = "\n".join(f"- {memory}" for memory in memories)
    return (
        "You are ARYA. Use the stored memories below when they are relevant. "
        "If they are not relevant, answer normally.\n\n"
        "Stored memories:\n"
        f"{memory_text}\n\n"
        "User message:\n"
        f"{message}"
    )


def ask_ai(message: str, memories: list[str] | None = None) -> str:
    """
    Send a message to the local Ollama model and return its text reply.

    Requires Ollama to be running locally with the qwen3:8b model pulled,
    e.g. via: `ollama run qwen3:8b`
    """
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": build_prompt(message, memories),
        "stream": False,
    }

    response = requests.post(url, json=payload, timeout=120)
    response.raise_for_status()

    data = response.json()
    return data.get("response", "").strip()
