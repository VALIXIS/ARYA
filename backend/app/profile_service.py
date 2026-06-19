"""
profile_service.py
------------------
Builds a simple user profile from stored memories using rule-based parsing.
"""


def _memory_content(memory) -> str:
    """Read memory content from either a SQLAlchemy object or a plain string."""
    return getattr(memory, "content", str(memory)).strip()


def _clean_value(value: str) -> str:
    """Clean an extracted profile value."""
    return value.strip(" \t\r\n.,!?;:")


def _add_unique(items: list[str], value: str) -> None:
    """Append a value if it is not already present, case-insensitively."""
    cleaned = _clean_value(value)
    if cleaned and cleaned.lower() not in {item.lower() for item in items}:
        items.append(cleaned)


def _format_section(title: str, items: list[str]) -> str:
    """Format one profile section."""
    if not items:
        return f"{title}: Not known yet"

    lines = "\n".join(f"- {item}" for item in items)
    return f"{title}:\n{lines}"


def build_profile(memories) -> str:
    """Build a formatted profile from stored memories."""
    profile = {
        "Name": [],
        "Likes": [],
        "Favourite things": [],
        "Goals": [],
        "Education": [],
        "Career ambitions": [],
    }

    for memory in memories:
        content = _memory_content(memory)
        lower_content = content.lower()

        if lower_content.startswith("my name is "):
            _add_unique(profile["Name"], content[len("my name is ") :])
        elif lower_content.startswith("i am ") and "student" in lower_content:
            _add_unique(profile["Education"], content)
        elif lower_content.startswith("i'm ") and "student" in lower_content:
            _add_unique(profile["Education"], content)
        elif lower_content.startswith("i like "):
            _add_unique(profile["Likes"], content[len("i like ") :])
        elif lower_content.startswith("my favourite "):
            _add_unique(profile["Favourite things"], content)
        elif lower_content.startswith("my favorite "):
            _add_unique(profile["Favourite things"], content)
        elif lower_content.startswith("my goal is "):
            _add_unique(profile["Goals"], content[len("my goal is ") :])
        elif lower_content.startswith("i want to "):
            _add_unique(profile["Goals"], content[len("i want to ") :])
        elif lower_content.startswith("my dream company is "):
            _add_unique(
                profile["Career ambitions"],
                f"Dream company: {content[len('my dream company is ') :]}",
            )
        elif "company" in lower_content or "career" in lower_content:
            _add_unique(profile["Career ambitions"], content)

    sections = [
        _format_section("Name", profile["Name"]),
        _format_section("Likes", profile["Likes"]),
        _format_section("Favourite things", profile["Favourite things"]),
        _format_section("Goals", profile["Goals"]),
        _format_section("Education", profile["Education"]),
        _format_section("Career ambitions", profile["Career ambitions"]),
    ]

    return "Your profile:\n\n" + "\n\n".join(sections)
