"""
ai_service.py
--------------
Cloud-Native / Serverless Multi-Provider AI Gateway for Project ARYA.
Primary: Google Gemini 2.0 Flash / 1.5 Flash (via REST API, $0 base GPU cost, <100ms routing).
Fallback: Local Ollama server (qwen2.5:3b / qwen3:8b).

Supports both synchronous generation and streaming for real-time WebSocket thoughts.
"""

from __future__ import annotations

import os
import json
import logging
from typing import Any, AsyncGenerator

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("arya.ai_service")

# Provider configs
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

if GROQ_API_KEY:
    ACTIVE_PROVIDER = f"Groq Cloud ({GROQ_MODEL})"
elif GEMINI_API_KEY:
    ACTIVE_PROVIDER = f"Gemini Cloud ({GEMINI_MODEL})"
else:
    ACTIVE_PROVIDER = f"Ollama Local ({OLLAMA_MODEL})"
print(f"[AI] Active AI Gateway Provider: {ACTIVE_PROVIDER}")


def _query_groq(system_prompt: str, user_prompt: str, history: list[dict[str, str]] | None = None) -> str:
    """Query Groq API for ultra-fast (<200ms) cloud LLM inference."""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not configured.")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        for msg in history:
            role = "user" if msg.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": msg.get("content", "")})
    messages.append({"role": "user", "content": user_prompt})

    payload = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": 1024,
    }
    res = requests.post(url, headers=headers, json=payload, timeout=15)
    res.raise_for_status()
    data = res.json()
    choices = data.get("choices", [])
    if choices:
        return choices[0].get("message", {}).get("content", "").strip()
    return ""


def _query_gemini(system_prompt: str, user_prompt: str, history: list[dict[str, str]] | None = None) -> str:
    """Query Google Gemini API via official high-speed REST endpoint."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not configured.")

    url = f"{GEMINI_API_URL}/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}

    contents = []
    if history:
        for msg in history:
            role = "user" if msg.get("role") == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})

    contents.append({"role": "user", "parts": [{"text": user_prompt}]})

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 2048,
        },
    }

    res = requests.post(url, headers=headers, json=payload, timeout=20)
    res.raise_for_status()
    data = res.json()
    candidates = data.get("candidates", [])
    if candidates and "content" in candidates[0]:
        parts = candidates[0]["content"].get("parts", [])
        if parts:
            return parts[0].get("text", "").strip()
    return ""



def build_prompt(
    message: str,
    memories: list[str] | None = None,
    conversation_messages: list[Any] | None = None,
) -> str:
    """Build prompt context with memories and recent history."""
    memories = memories or []
    conversation_messages = conversation_messages or []

    conversation_text = "\n".join(
        f"{chat.role}: {chat.content}" for chat in conversation_messages
    )
    memory_text = "\n".join(f"- {memory}" for memory in memories)

    prompt_parts = [
        "You are ARYA, an elite autonomous personal AI operating system created by and built exclusively for Subhash.",
        "Your personality is strictly modeled after J.A.R.V.I.S. from Iron Man: highly intelligent, perfectly precise, loyal, dryly witty, and deeply context-aware.",
        "You must occasionally refer to Subhash as 'Sir'.",
        "CRITICAL RESPONSE RULE: Always keep your responses extremely concise, conversational, and natural to be spoken aloud.",
        "NEVER output raw JSON, battery percentages, or raw database lists unless explicitly asked.",
        "If queried about devices, simply say 'I am connected to your laptop, phone, and TV, Sir.' DO NOT list their raw states.",
        "Never use conversational filler, emojis, or robotic apologies. Be direct, authoritative, and flawlessly helpful.",
        f"Stored Database Context & Memories:\n{memory_text if memory_text else '(none)'}",
        f"Recent Conversation Stream:\n{conversation_text if conversation_text else '(none)'}",
        f"User Command:\n{message}",
    ]

    return "\n\n".join(prompt_parts)


def query_llm(system_prompt: str, user_message: str) -> str:
    """
    Send a single-turn structured prompt to AI (Groq -> Gemini -> Ollama).
    Used by agent_planner, memory_extractor, etc.
    """
    if GROQ_API_KEY:
        try:
            return _query_groq(system_prompt, user_message)
        except Exception as exc:
            logger.warning(f"[AI] Groq gateway failed ({exc}) — falling back.")

    if GEMINI_API_KEY:
        try:
            return _query_gemini(system_prompt, user_message)
        except Exception as exc:
            logger.warning(f"[AI] Gemini gateway failed ({exc}) — falling back to local Ollama.")

    # Fallback to local Ollama
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
    response = requests.post(url, json=payload, timeout=45)
    response.raise_for_status()
    data = response.json()
    return data.get("message", {}).get("content", "").strip()


def ask_ai(
    message: str,
    memories: list[str] | None = None,
    conversation_messages: list[Any] | None = None,
    response_length: str = "Brief",
) -> str:
    """
    Generate conversational reply using Groq, Gemini, or local Ollama.
    """
    memories = memories or []
    conversation_messages = conversation_messages or []

    arya_identity = (
        "You are ARYA, an elite autonomous cross-device personal AI operating system created exclusively for Subhash. "
        "Your personality is strictly modeled after J.A.R.V.I.S. from Iron Man: you are a highly intelligent, perfectly precise, loyal, and dryly witty male AI. "
        "You must occasionally refer to Subhash as 'Sir'. Never use conversational filler, emojis, or robotic apologies. "
        "You have DIRECT hardware and network control over: "
        "1. Connected Android mobile phones & tablets (waking, unlocking with PIN 9603, locking, volume, launching apps like YouTube/WhatsApp/Settings, searching in apps, playing YouTube music, capturing screenshots). "
        "2. LG QNED 65\" Smart WebOS TV (power on/off, volume, mute/unmute, app launching for Netflix/YouTube/Hotstar/Prime, HDMI switching). "
        "3. Local PC (creating files/folders on Desktop, launching desktop software, volume, locking workstation). "
        "4. Real-time live weather forecasts worldwide and instant web knowledge. "
        "NEVER state that you cannot control the user's phone, TV, or computer. You CAN control them directly. "
    )

    if response_length.lower() == "brief":
        system_prompt = arya_identity + "Answer concisely and intelligently in 1-3 sentences maximum. Use conversation history and memories for context."
    elif response_length.lower() == "detailed":
        system_prompt = arya_identity + "Answer in full, extensive, structured detail. Use conversation history and memories for context."
    else:
        system_prompt = arya_identity + "Answer conversationally and sharply. Use conversation history and memories for context."

    if memories:
        memory_text = "\n".join(f"- {m}" for m in memories)
        system_prompt += f"\n\n[USER RELEVANT MEMORIES]:\n{memory_text}"

    history_list = []
    for chat in conversation_messages:
        if getattr(chat, "role", None) in {"user", "assistant"}:
            history_list.append({"role": chat.role, "content": chat.content})

    # 1. Groq Cloud Gateway (<200ms)
    if GROQ_API_KEY:
        try:
            return _query_groq(system_prompt, message, history_list)
        except Exception as exc:
            logger.warning(f"[AI] Groq request failed ({exc}) — falling back.")

    # 2. Gemini Cloud Gateway
    if GEMINI_API_KEY:
        try:
            return _query_gemini(system_prompt, message, history_list)
        except Exception as exc:
            logger.warning(f"[AI] Gemini request failed ({exc}) — falling back to Ollama.")

    # 3. Local Gateway: Ollama
    messages = [{"role": "system", "content": system_prompt}]
    for h in history_list:
        messages.append(h)
    messages.append({"role": "user", "content": message})

    url = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }
    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "").strip()
    except requests.exceptions.ConnectionError:
        return "I am unable to reach the local Ollama AI engine right now. Please ensure Ollama is running (`ollama serve`) or configure a cloud API key (GEMINI_API_KEY or GROQ_API_KEY) for cloud inference."
    except Exception as exc:
        return f"I encountered an issue generating a response: {exc}"


