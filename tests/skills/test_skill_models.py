"""Tests for the Skill model.

API these tests pin down:

    Skill(name: str, description: str, path: Path)
    .directory -> Path        # the folder that holds SKILL.md

`path` is the SKILL.md file. `directory` is a derived fact (no new stored field).
"""

from pathlib import Path

from app.skills import Skill

# --- Phase 1: directory is the folder of SKILL.md ----------------------------


def test_directory_is_the_folder_that_holds_skill_md():
    skill = Skill("apple", "Does things.", Path(".claude/skills/apple/SKILL.md"))

    assert skill.directory == Path(".claude/skills/apple")
