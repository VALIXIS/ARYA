"""
memory_deduplicator.py
-----------------------
Semantic (fact-aware) deduplication for ARYA's memory store.

Strategy (no external embeddings required):
  1. Normalise both memories: lowercase, strip punctuation, collapse whitespace.
  2. Substring test:
       - If existing_normalised ⊂ new_normalised  → new is MORE detailed.
         Delete the old one and save the new one.
       - If new_normalised ⊂ existing_normalised  → existing is MORE detailed.
         Skip saving the new one.
  3. Jaccard word-overlap ≥ 0.80  → probably the same fact.
       Keep the LONGER (more detailed) version.

Fact-aware guard — we do NOT merge when the memories carry DIFFERENT values
for the same attribute.  Example:
   "My favourite actor is Prabhas"  vs  "My favourite actor is Mahesh Babu"
Both share a high overlap on "my favourite actor is" but their values differ.
We detect this by checking whether the *differing* words look like proper nouns
or numeric values. If so, we treat the new memory as an UPDATE (the newer value
supersedes the older one) rather than a plain duplicate.

UPDATE semantics (conflicting values):
   "My laptop has 16GB RAM"  →  "My laptop has 32GB RAM"
   The old memory is deleted and the new one is saved (user corrected info).
"""

import re
import string


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _word_set(normalised: str) -> set[str]:
    return set(normalised.split())


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


# Words that are unlikely to be unique values (stop words + common
# memory-phrasing words). Differing words NOT in this set are treated as
# value tokens.
_FILLER = {
    "my", "i", "am", "is", "are", "was", "a", "an", "the", "of", "and",
    "to", "in", "at", "by", "for", "on", "with", "have", "has", "be",
    "favourite", "favorite", "love", "like", "enjoy", "prefer", "study",
    "studying", "studying", "work", "working", "built", "building",
    "laptop", "phone", "pc", "desktop", "device", "computer",
    "dream", "goal", "plan", "aspire", "want", "become",
}


def _value_tokens(word_set: set[str]) -> set[str]:
    """Words that are likely to carry the *value* of a fact."""
    return word_set - _FILLER


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Result codes returned by check_duplicate
SKIP  = "skip"    # new is redundant — existing is already more detailed
MERGE = "merge"   # new replaces existing (new is more detailed / updated)
SAVE  = "save"    # not a duplicate — save normally


def check_duplicate(
    new_content: str,
    existing_memories: list,
) -> tuple[str, object | None]:
    """
    Compare *new_content* against the list of existing MemorySnapshot objects.

    Returns (action, target_memory):
      - (SKIP,  None)    → don't save; existing already covers it
      - (MERGE, memory)  → delete *memory* then save the new one
      - (SAVE,  None)    → no duplicate found; proceed with normal save
    """
    new_norm = _normalise(new_content)
    new_words = _word_set(new_norm)
    new_values = _value_tokens(new_words)

    for mem in existing_memories:
        ex_norm = _normalise(mem.content)
        ex_words = _word_set(ex_norm)
        ex_values = _value_tokens(ex_words)

        # --- 1. Exact-normalised match (already handled upstream, but be safe)
        if new_norm == ex_norm:
            print(f"[DEDUP] Exact duplicate skipped: {new_content!r}")
            return SKIP, None

        # --- 2. Substring test -------------------------------------------
        new_in_ex = new_norm in ex_norm   # new is a strict subset of existing
        ex_in_new = ex_norm in new_norm   # existing is a strict subset of new

        if new_in_ex:
            # Existing is more detailed — skip new
            print(f"[DEDUP] SKIP -- existing is superset: {mem.content!r}")
            return SKIP, None

        if ex_in_new:
            # New is more detailed — check value conflict first
            diff_values_ex = ex_values - new_values
            diff_values_new = new_values - ex_values

            # If existing has unique value tokens not in new, it could be a
            # different fact (shouldn't happen with substring, but guard anyway)
            if diff_values_ex:
                # Existing carries values the new one doesn't — treat as update
                print(
                    f"[DEDUP] MERGE (update, new is superset with new values) "
                    f"{mem.content!r} -> {new_content!r}"
                )
                return MERGE, mem

            print(
                f"[DEDUP] MERGE (new is superset) "
                f"{mem.content!r} -> {new_content!r}"
            )
            return MERGE, mem

        # --- 3. Jaccard overlap ------------------------------------------
        jaccard = _jaccard(new_words, ex_words)
        if jaccard < 0.80:
            continue   # not similar enough — definitely not the same fact

        # High overlap.  Now check if they carry DIFFERENT values.
        diff_new = new_values - ex_values   # value tokens only in new
        diff_ex  = ex_values  - new_values  # value tokens only in existing

        if diff_new and diff_ex:
            # Both memories have unique value tokens -> different values for
            # the same attribute.
            # Treat as an UPDATE: new information replaces old.
            print(
                f"[DEDUP] UPDATE (conflicting values, new replaces old) "
                f"{mem.content!r} -> {new_content!r}"
            )
            return MERGE, mem

        # Same values (or one is just more wordy) -> keep the longer one
        if len(new_content) >= len(mem.content):
            print(
                f"[DEDUP] MERGE (high Jaccard, new is longer) "
                f"{mem.content!r} -> {new_content!r}"
            )
            return MERGE, mem
        else:
            print(
                f"[DEDUP] SKIP (high Jaccard, existing is longer) "
                f"existing={mem.content!r}, new={new_content!r}"
            )
            return SKIP, None

    return SAVE, None
