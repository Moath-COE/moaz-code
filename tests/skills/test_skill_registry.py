"""Tests for SkillRegistry: lookup (get) and advertisement (render).

API these tests pin down:

    SkillRegistry(skills: list[Skill])
    .get(name: str) -> Skill | None
    .render() -> str
"""

from pathlib import Path

import pytest

from app.skills import Skill, SkillRegistry, SkillsLoader


def make_skill(name: str, description: str = "Does things.") -> Skill:
    """A Skill whose file does not exist: the registry must never read it."""
    return Skill(name, description, Path(f"{name}/SKILL.md"))


# --- get ---------------------------------------------------------------------


def test_get_returns_a_known_skill():
    apple = make_skill("apple")

    assert SkillRegistry([apple, make_skill("grape")]).get("apple") is apple


def test_get_returns_none_for_an_unknown_name():
    assert SkillRegistry([make_skill("apple")]).get("banana") is None


# --- render (exact text, the tester depends on it) ---------------------------


def test_render_matches_the_required_format():
    registry = SkillRegistry(
        [
            make_skill("apple", "Deploys the apple service to production."),
            make_skill("grape", "Runs the grape test suite and reports failures."),
        ]
    )

    assert registry.render() == (
        "You have access to the following skills:\n"
        "\n"
        "- apple: Deploys the apple service to production.\n"
        "- grape: Runs the grape test suite and reports failures."
    )


def test_render_lists_skills_sorted_by_name():
    registry = SkillRegistry([make_skill("grape"), make_skill("apple")])

    lines = registry.render().splitlines()[2:]

    assert [line.split(":")[0] for line in lines] == ["- apple", "- grape"]


def test_render_with_no_skills_is_empty():
    # No header with nothing under it. Empty means "send no system message".
    assert SkillRegistry([]).render() == ""


def test_render_does_not_include_the_body(tmp_path):
    skill_dir = tmp_path / "apple"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\ndescription: Deploys apple.\n---\n\nSECRET BODY TEXT\n",
        encoding="utf-8",
    )

    text = SkillRegistry(SkillsLoader([tmp_path]).load()).render()

    assert "SECRET BODY TEXT" not in text


def test_render_keeps_a_multiline_description_on_one_line(tmp_path):
    skill_dir = tmp_path / "apple"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\ndescription: |\n  Line one.\n  Line two.\n---\nbody\n",
        encoding="utf-8",
    )

    text = SkillRegistry(SkillsLoader([tmp_path]).load()).render()

    assert "- apple: Line one. Line two." in text


# --- get_instructions: header + body (disclosure level 3 support) -------------
#
# API: SkillRegistry.get_instructions(name) -> str | None
#
# What the model sees when a skill is invoked: a header naming the skill's
# folder (so relative paths like `scripts/x.sh` can be resolved), then the body.
# Exact format, from the stage:
#
#   Skill: apple (located at .claude/skills/apple)
#   Paths in the instructions below are relative to that folder.
#   <blank line>
#   <body>
#
# Work through the phases in order. Uncomment ONE, watch it fail, make it pass.


def write_skill_file(root: Path, name: str, body: str) -> None:
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\ndescription: Does things.\n---\n\n{body}\n", encoding="utf-8"
    )


# --- Phase 3: the header names the skill's folder ----------------------------


def test_get_instructions_starts_with_the_skill_folder_header(tmp_path):
    write_skill_file(tmp_path, "apple", "Run `scripts/checksum.sh`.")
    registry = SkillRegistry(SkillsLoader([tmp_path]).load())

    first_two_lines = registry.get_instructions("apple").splitlines()[:2]

    assert first_two_lines == [
        f"Skill: apple (located at {tmp_path / 'apple'})",
        "Paths in the instructions below are relative to that folder.",
    ]


# --- Phase 4: the body follows the header, untouched -------------------------


def test_get_instructions_ends_with_the_body_after_a_blank_line(tmp_path):
    write_skill_file(tmp_path, "apple", "Run `scripts/checksum.sh`.")
    registry = SkillRegistry(SkillsLoader([tmp_path]).load())

    text = registry.get_instructions("apple")

    assert text.endswith("relative to that folder.\n\nRun `scripts/checksum.sh`.")


# --- Phase 5: a relative root gives a relative folder (the real scenario) ----


def test_header_uses_the_path_as_discovered_not_an_absolute_one(tmp_path, monkeypatch):
    # The tester expects `.claude/skills/apple`, relative to the project root.
    monkeypatch.chdir(tmp_path)
    write_skill_file(Path(".claude/skills"), "apple", "body")
    registry = SkillRegistry(SkillsLoader([Path(".claude/skills")]).load())

    header = registry.get_instructions("apple").splitlines()[0]

    assert header == "Skill: apple (located at .claude/skills/apple)"


def test_get_instructions_returns_the_skill_body_without_frontmatter(tmp_path):
    skill_dir = tmp_path / "apple"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\ndescription: Deploys apple.\n---\n\nSay blueberry.\n", encoding="utf-8"
    )
    registry = SkillRegistry(SkillsLoader([tmp_path]).load())

    # The full text pins both halves: our header, then the body with no frontmatter.
    assert registry.get_instructions("apple") == (
        f"Skill: apple (located at {tmp_path / 'apple'})\n"
        "Paths in the instructions below are relative to that folder.\n"
        "\n"
        "Say blueberry."
    )


def test_get_instructions_of_an_unreadable_skill_raises_runtime_error():
    registry = SkillRegistry([make_skill("apple")])  # file does not exist

    with pytest.raises(RuntimeError, match="apple"):
        registry.get_instructions("apple")
