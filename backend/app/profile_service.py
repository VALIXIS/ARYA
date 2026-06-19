"""
profile_service.py
------------------
Builds a simple user profile from stored memories using category grouping.
"""

def _format_section(title: str, items: list[str]) -> str:
    """Format one profile section."""
    if not items:
        return f"{title}:\n- Not known yet"

    lines = "\n".join(f"- {item}" for item in items)
    return f"{title}:\n{lines}"

def build_profile(memories) -> str:
    """Build a formatted profile from stored memories grouped by category."""
    categories = {
        "Identity": [],
        "Preferences": [],
        "Education": [],
        "Interests": [],
        "Projects": [],
        "Goals": [],
        "Career": [],
        "Devices": [],
        "Other": []
    }

    for memory in memories:
        content = getattr(memory, "content", str(memory)).strip()
        category = getattr(memory, "category", "Other")
        
        # Fallback for old memories without a valid category
        if category not in categories:
            category = "Other"
            
        if content not in categories[category]:
            categories[category].append(content)

    print(f"[PROFILE] Categories loaded: {list(categories.keys())}")

    sections = [
        _format_section("Identity", categories["Identity"]),
        _format_section("Preferences", categories["Preferences"]),
        _format_section("Education", categories["Education"]),
        _format_section("Interests", categories["Interests"]),
        _format_section("Projects", categories["Projects"]),
        _format_section("Goals", categories["Goals"]),
        _format_section("Career", categories["Career"]),
        _format_section("Devices", categories["Devices"]),
    ]
    
    if categories["Other"]:
        sections.append(_format_section("Other", categories["Other"]))

    return "Your profile:\n\n" + "\n\n".join(sections)

