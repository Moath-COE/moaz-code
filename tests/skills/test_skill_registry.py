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


# --- get_body ----------------------------------------------------------------


def test_get_body_returns_the_skill_body_without_frontmatter(tmp_path):
    skill_dir = tmp_path / "apple"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\ndescription: Deploys apple.\n---\n\nSay blueberry.\n", encoding="utf-8"
    )
    registry = SkillRegistry(SkillsLoader([tmp_path]).load())

    assert registry.get_body("apple") == "Say blueberry."


def test_get_body_of_an_unknown_name_is_none():
    assert SkillRegistry([make_skill("apple")]).get_body("banana") is None


def test_get_body_of_an_unreadable_skill_raises_runtime_error():
    registry = SkillRegistry([make_skill("apple")])  # file does not exist

    with pytest.raises(RuntimeError, match="apple"):
        registry.get_body("apple")


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
