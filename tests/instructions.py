"""Single source of truth for the text SkillRegistry wraps around a skill body.

Tests build the expected message here, so a wording change in the registry
needs one edit in this file instead of one per assertion.
"""

from pathlib import Path

HEADER_BODY_SEPARATOR = "\n\nSkill instructions:\n"


def expected_header(skill_dir: Path, name: str = "apple") -> str:
    """The two header lines, ending right before the blank line."""
    return (
        f"Skill: {name} (located at {skill_dir / name})\n"
        "Paths in the instructions below are relative to that folder."
    )


def expected_instructions(skill_dir: Path, body: str, name: str = "apple") -> str:
    """The full message for a skill stored at `skill_dir / name`."""
    return expected_header(skill_dir, name) + HEADER_BODY_SEPARATOR + body
