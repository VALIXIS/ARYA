"""
ai_service.py
--------------
Handles all communication with the local Ollama server running the
qwen3:8b model. This keeps AI-specific code isolated from the rest
of the app, so the model or provider can be changed later without
touching the API routes.
"""

import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
print(f"[AI] Model: {OLLAMA_MODEL}")


def build_prompt(
    message: str,
    memories: list[str] | None = None,
    conversation_messages: list[Any] | None = None,
) -> str:
    """Build the prompt sent to Qwen with stronger reference resolution rules."""
    memories = memories or []
    conversation_messages = conversation_messages or []

    conversation_text = "\n".join(
        f"{chat.role}: {chat.content}" for chat in conversation_messages
    )
    memory_text = "\n".join(f"- {memory}" for memory in memories)

    prompt_parts = [
        (
            "You are ARYA.\n\n"
            "Always use the Recent Conversation section first when answering.\n\n"
            "If the current question refers to:\n"
            "- it\n"
            "- that\n"
            "- this\n"
            "- they\n"
            "- them\n"
            "- he\n"
            "- she\n\n"
            "resolve the reference using the recent conversation before answering.\n\n"
            "Never invent information when the answer exists in conversation history."
        ),
        f"Recent Conversation:\n{conversation_text if conversation_text else '(none)'}",
        f"Stored Memories:\n{memory_text if memory_text else '(none)'}",
        f"Current User Message:\n{message}",
    ]

    return "\n\n".join(prompt_parts)


def query_llm(system_prompt: str, user_message: str) -> str:
    """
    Send a single-turn message to Ollama with a custom system prompt.
    No memories, no conversation history injected.
    Used by memory_extractor and action_planner for structured JSON tasks.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }
    response = requests.post(url, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    return data.get("message", {}).get("content", "").strip()


def ask_ai(
    message: str,
    memories: list[str] | None = None,
    conversation_messages: list[Any] | None = None,
) -> str:
    """
    Send a message to the local Ollama model and return its text reply.

    Requires Ollama to be running locally with the qwen3:8b model pulled,
    e.g. via: `ollama run qwen3:8b`
    """
    memories = memories or []
    conversation_messages = conversation_messages or []

    system_prompt = (
        "You are ARYA.\n\n"
        "Always use the recent conversation first when answering.\n\n"
        "If the current question refers to it, that, this, they, them, he, or she, "
        "resolve the reference using the recent conversation before answering.\n\n"
        "Never invent information when the answer exists in conversation history."
    )

    messages = [{"role": "system", "content": system_prompt}]

    if memories:
        memory_text = "\n".join(f"- {memory}" for memory in memories)
        messages.append(
            {
                "role": "system",
                "content": f"Stored Memories:\n{memory_text}",
            }
        )

    for chat in conversation_messages:
        if chat.role in {"user", "assistant"}:
            messages.append({"role": chat.role, "content": chat.content})

    messages.append({"role": "user", "content": message})

    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }

    response = requests.post(url, json=payload, timeout=120)
    response.raise_for_status()

    data = response.json()
    return data.get("message", {}).get("content", "").strip()
