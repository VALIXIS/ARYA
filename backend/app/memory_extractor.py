"""
memory_extractor.py
-------------------
Lightweight rule-based extraction for personal facts.
No AI calls, embeddings, or NLP libraries are used here.
"""


PERSONAL_FACT_PREFIXES = (
    "i am ",
    "i'm ",
    "i like ",
    "my favourite ",
    "my favorite ",
    "my dream company is ",
)


def _clean_memory(message: str) -> str:
    """Clean a detected memory before saving it."""
    return message.strip(" \t\r\n.,!?;:")


def extract_memory(message: str) -> str | None:
    """Extract a simple personal fact from a user message."""
    text = _clean_memory(message)
    lower_text = text.lower()

    for prefix in PERSONAL_FACT_PREFIXES:
        if lower_text.startswith(prefix):
            return text

    return None
