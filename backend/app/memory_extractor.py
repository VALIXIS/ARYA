"""
memory_extractor.py
-------------------
Extracts personal facts using rule-based pattern matching.
No LLM call needed for extraction — patterns are fast and reliable.

The classifier layer (LLM) was found to be unreliable with smaller models
(qwen2.5:3b returns {} for all inputs). Pattern matching is used instead.
"""

import re
import json
from .ai_service import query_llm
from .memory_validator import ALLOWED_CATEGORIES

print("[BOOT] memory_extractor loaded")

# (regex_pattern, category)
FACT_PATTERNS = [
    # Identity
    (r"^my name is (.+)$",                  "Identity"),
    (r"^call me (.+)$",                     "Identity"),
    (r"^i(?:'m| am) (.+)$",                "Identity"),
    (r"^i go by (.+)$",                     "Identity"),
    (r"^people call me (.+)$",              "Identity"),

    # Education
    (r"^i(?:'m| am) (?:a )?student(?: of (.+))?$",  "Education"),
    (r"^i study (.+)$",                     "Education"),
    (r"^i(?:'m| am) studying (.+)$",        "Education"),
    (r"^i(?:'m| am) pursuing (.+)$",        "Education"),
    (r"^i(?:'m| am) doing (.+) (?:course|degree|program)$", "Education"),

    # Goals
    (r"^i want to (?:become|be) (.+)$",     "Goals"),
    (r"^my goal is to (.+)$",               "Goals"),
    (r"^my dream is to (.+)$",              "Goals"),
    (r"^i aspire to (.+)$",                 "Goals"),
    (r"^i plan to (.+)$",                   "Goals"),

    # Career
    (r"^i work (?:as |at |in )(.+)$",       "Career"),
    (r"^i(?:'m| am) a (.+) (?:by profession|professionally)$", "Career"),
    (r"^my dream (?:job|company) is (.+)$", "Career"),
    (r"^i(?:'m| am) (?:an? )?(.+) engineer$", "Career"),

    # Interests
    (r"^i love (.+)$",                      "Interests"),
    (r"^i enjoy (.+)$",                     "Interests"),
    (r"^i(?:'m| am) (?:into|passionate about) (.+)$", "Interests"),
    (r"^i(?:'m| am) interested in (.+)$",  "Interests"),

    # Preferences
    (r"^i like (.+)$",                      "Preferences"),
    (r"^i prefer (.+)$",                    "Preferences"),
    (r"^i(?:'m| am) a fan of (.+)$",        "Preferences"),
    (r"^my favou?rite (.+) is (.+)$",       "Preferences"),
    (r"^i don't like (.+)$",               "Preferences"),
    (r"^i dislike (.+)$",                  "Preferences"),

    # Devices
    (r"^i have (?:a |an |my )?(.+(?:laptop|phone|pc|desktop|tablet|device|computer|headphones|keyboard|monitor).*)$", "Devices"),
]

def _build_llm_prompt() -> str:
    return """You are ARYA's memory extraction subsystem.
Extract personal facts from the user's text.
Output MUST be a valid JSON array of objects. Do not include markdown fences.
Valid categories: Identity, Preferences, Education, Interests, Projects, Goals, Career, Devices.
Do NOT use any other category. If a fact does not fit, omit it.
Do NOT extract commands, dates, current locations, weather, or temporary states.

Example input:
I built Planly and ARYA.

Example output:
[
  {"content": "Built Planly and ARYA", "category": "Projects"}
]"""

def extract_memories(message: str) -> list[dict]:
    """
    Extract personal facts using a Hybrid approach:
    1. Regex pattern matching per line.
    2. LLM extraction for unmatched lines.
    Returns a list of dicts: [{'content': '...', 'category': '...'}, ...]
    """
    results = []
    unmatched_lines = []
    
    # Split by simple punctuation to evaluate sentence/lines
    # But keep it simple: split by newline first. The user example uses newlines.
    lines = [line.strip() for line in message.replace(".", "\n").split('\n') if line.strip()]
    
    for line in lines:
        lower_line = line.lower()
        matched = False
        
        for pattern, category in FACT_PATTERNS:
            if re.match(pattern, lower_line, re.IGNORECASE):
                results.append({"content": line, "category": category})
                print(f"[MEMORY] Pattern matched: {pattern!r} -> category={category!r}, content={line!r}")
                matched = True
                break
                
        if not matched:
            unmatched_lines.append(line)
            
    # Priority 2: LLM
    if unmatched_lines:
        unmatched_text = "\n".join(unmatched_lines)
        print(f"[MEMORY] Sending to LLM for extraction: {unmatched_text!r}")
        try:
            raw = query_llm(_build_llm_prompt(), unmatched_text).strip()
            
            # Clean markdown
            clean = raw
            for fence in ("```json", "```"):
                if clean.startswith(fence):
                    clean = clean[len(fence):]
            if clean.endswith("```"):
                clean = clean[:-3]
            clean = clean.strip()
            
            data = json.loads(clean)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "content" in item and "category" in item:
                        cat = str(item["category"])
                        if cat not in ALLOWED_CATEGORIES:
                            print(f"[MEMORY] LLM item dropped (bad category {cat!r}): {item['content']!r}")
                            continue
                        print(f"[MEMORY] LLM Extracted: category={cat!r}, content={item['content']!r}")
                        results.append({"content": str(item["content"]), "category": cat})
        except Exception as exc:
            print(f"[MEMORY] LLM extraction failed: {exc}")
            
    if results:
        print(f"[MEMORY] Extracted {len(results)} memories")
            
    return results
