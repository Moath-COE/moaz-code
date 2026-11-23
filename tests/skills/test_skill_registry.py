"""Tests for SkillRegistry: lookup (get) and advertisement (render).

API these tests pin down:

    SkillRegistry(skills: list[Skill])
    .get(name: str) -> Skill | None
    .render() -> str
"""

from pathlib import Path

import pytest

from app.skills import Skill, SkillRegistry, SkillsLoader
from tests.instructions import HEADER_BODY_SEPARATOR, expected_instructions


def make_skill(name: str, description: str = "Does things.") -> Skill:
    """A Skill whose file does not exist: the registry must never read it."""
    return Skill(name, description, Path(f"{name}/SKILL.md"))


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


# --- _get_instructions: header + body (disclosure level 3 support) -------------
#
# API: SkillRegistry._get_instructions(name) -> str | None
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


def test__get_instructions_starts_with_the_skill_folder_header(tmp_path):
    write_skill_file(tmp_path, "apple", "Run `scripts/checksum.sh`.")
    registry = SkillRegistry(SkillsLoader([tmp_path]).load())

    first_two_lines = registry._get_instructions("apple").splitlines()[:2]

    assert first_two_lines == [
        f"Skill: apple (located at {tmp_path / 'apple'})",
        "Paths in the instructions below are relative to that folder.",
    ]


# --- Phase 4: the body follows the header, untouched -------------------------


def test__get_instructions_ends_with_the_body_after_a_blank_line(tmp_path):
    write_skill_file(tmp_path, "apple", "Run `scripts/checksum.sh`.")
    registry = SkillRegistry(SkillsLoader([tmp_path]).load())

    text = registry._get_instructions("apple")

    assert text == expected_instructions(tmp_path, "Run `scripts/checksum.sh`.")


# --- Phase 5: a relative root gives a relative folder (the real scenario) ----


def test_header_uses_the_path_as_discovered_not_an_absolute_one(tmp_path, monkeypatch):
    # The tester expects `.claude/skills/apple`, relative to the project root.
    monkeypatch.chdir(tmp_path)
    write_skill_file(Path(".claude/skills"), "apple", "body")
    registry = SkillRegistry(SkillsLoader([Path(".claude/skills")]).load())

    header = registry._get_instructions("apple").splitlines()[0]

    assert header == "Skill: apple (located at .claude/skills/apple)"


def test__get_instructions_returns_the_skill_body_without_frontmatter(tmp_path):
    skill_dir = tmp_path / "apple"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\ndescription: Deploys apple.\n---\n\nSay blueberry.\n", encoding="utf-8"
    )
    registry = SkillRegistry(SkillsLoader([tmp_path]).load())

    # The full text pins both halves: our header, then the body with no frontmatter.
    assert registry._get_instructions("apple") == expected_instructions(
        tmp_path, "Say blueberry."
    )


def test__get_instructions_of_an_unreadable_skill_raises_runtime_error():
    registry = SkillRegistry([make_skill("apple")])  # file does not exist

    with pytest.raises(RuntimeError, match="apple"):
        registry._get_instructions("apple")


# --- expand: instructions with arguments filled in -----------------------------
#
# API: SkillRegistry.expand(name: str, args: str = "") -> str | None
#
# The one place that turns "skill name + argument text" into the final text the
# model sees. Gate (/name) and the future Skill tool both call it.
#
#   - unknown name -> None (the caller decides how to report it)
#   - known name   -> _get_instructions(name) with the placeholders
#                     ($ARGUMENTS, $ARGUMENTS[N], $N) filled from `args`
#
# Work through the phases in order. Uncomment ONE, watch it fail, make it pass.


def registry_with(tmp_path: Path, body: str, name: str = "apple") -> SkillRegistry:
    write_skill_file(tmp_path, name, body)
    return SkillRegistry(SkillsLoader([tmp_path]).load())


# --- Phase 7: no placeholders -> exactly _get_instructions --------------------


def test_expand_without_placeholders_equals__get_instructions(tmp_path):
    registry = registry_with(tmp_path, "Say blueberry.")

    assert registry.expand("apple", "ignored") == registry._get_instructions("apple")


# --- Phase 8: $ARGUMENTS gets the whole argument text ------------------------


def test_expand_fills_the_arguments_placeholder(tmp_path):
    registry = registry_with(tmp_path, "Checksum of $ARGUMENTS")

    assert registry.expand("apple", "data.txt").endswith(
        HEADER_BODY_SEPARATOR + "Checksum of data.txt"
    )


def test_expand_keeps_the_original_spacing_in_arguments(tmp_path):
    registry = registry_with(tmp_path, "[$ARGUMENTS]")

    assert registry.expand("apple", "a   b").endswith("[a   b]")


# --- Phase 9: positional placeholders ----------------------------------------


def test_expand_fills_positional_placeholders_in_the_order_the_body_asks(tmp_path):
    registry = registry_with(tmp_path, "$1 $0")

    assert registry.expand("apple", "mango pear").endswith(
        HEADER_BODY_SEPARATOR + "pear mango"
    )


# --- Phase 10: no arguments -> placeholders become empty ---------------------


def test_expand_defaults_to_no_arguments(tmp_path):
    registry = registry_with(tmp_path, "[$ARGUMENTS][$0]")

    assert registry.expand("apple").endswith("[][]")


def test_expand_with_too_few_words_gives_empty_strings(tmp_path):
    registry = registry_with(tmp_path, "[$0][$1]")

    assert registry.expand("apple", "only").endswith("[only][]")


# --- Phase 11: the folder header is kept -------------------------------------


def test_expand_keeps_the_folder_header(tmp_path):
    registry = registry_with(tmp_path, "Checksum of $ARGUMENTS")

    assert registry.expand("apple", "data.txt").startswith(
        f"Skill: apple (located at {tmp_path / 'apple'})\n"
    )


# --- Phase 12: failures are not swallowed ------------------------------------


def test_expand_of_an_unreadable_skill_raises_runtime_error():
    registry = SkillRegistry([make_skill("apple")])  # file does not exist

    with pytest.raises(RuntimeError, match="apple"):
        registry.expand("apple", "x")


# --- contains: the single existence check ------------------------------------


def test_contains_is_true_for_a_known_name():
    assert "apple" in SkillRegistry([make_skill("apple")])


def test_contains_is_false_for_an_unknown_name():
    assert "banana" not in SkillRegistry([make_skill("apple")])


# --- expand: unknown name is an error, not None ------------------------------


def test_expand_raises_for_an_unknown_name():
    # make_skill's file does not exist: an unknown name must not read anything.
    with pytest.raises(ValueError, match="banana"):
        SkillRegistry([make_skill("apple")]).expand("banana", "x")
