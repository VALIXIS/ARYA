import os
import base64
import requests
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any

from app.android_service import android_bridge
from app.ai_service import GEMINI_API_KEY, GEMINI_API_URL, GEMINI_MODEL

logger = logging.getLogger("arya.vision")

def _encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def analyze_image_with_gemini(image_path: str, prompt: str) -> str:
    if not GEMINI_API_KEY:
        return "Gemini API key is not configured for Vision."
        
    url = f"{GEMINI_API_URL}/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    
    base64_img = _encode_image(image_path)
    
    payload = {
        "contents": [{
            "role": "user",
            "parts": [
                {"text": prompt},
                {"inlineData": {
                    "mimeType": "image/png",
                    "data": base64_img
                }}
            ]
        }],
        "generationConfig": {"temperature": 0.4}
    }
    
    try:
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        res.raise_for_status()
        data = res.json()
        candidates = data.get("candidates", [])
        if candidates and "content" in candidates[0]:
            parts = candidates[0]["content"].get("parts", [])
            if parts:
                return parts[0].get("text", "").strip()
        return "No insights returned by Vision model."
    except Exception as e:
        logger.error(f"Vision API error: {e}")
        return f"Vision processing failed: {e}"

def analyze_phone_screen(prompt: str = "Analyze this screenshot. What is currently on the screen? Give a concise summary.") -> Dict[str, Any]:
    fd, shot_path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    
    res = android_bridge.take_screenshot(shot_path)
    if not res.get("success"):
        return {"success": False, "message": "Failed to capture phone screen."}
        
    analysis = analyze_image_with_gemini(shot_path, prompt)
    
    try:
        os.remove(shot_path)
    except:
        pass
        
    return {"success": True, "message": analysis}
