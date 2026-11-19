"""Tests for Gate: what the model sees in place of the raw user prompt.

API these tests pin down:

    Gate(skills: list[Skill]).parse_user_prompt(prompt: str) -> str

Rules:
    - "/<name>" (optionally followed by words) where <name> is a known skill
      -> the skill's body, and nothing else.
    - anything else -> the prompt, unchanged.

Work through the steps in order. Uncomment ONE step, watch it fail, then make
it pass. Do not uncomment the next step until the current one is green.
"""

from pathlib import Path

import pytest

from app.input.gate import Gate
from app.skills import Skill, SkillsLoader


@pytest.fixture
def gate() -> Gate:
    """A gate whose skill files do NOT exist. Fine for pass-through tests,
    because a prompt that is not expanded never reads a file."""
    return Gate(skills=[Skill("apple", "Deploys apple.", Path("a/SKILL.md"))])


def gate_with_skills(root: Path, bodies: dict[str, str]) -> Gate:
    """Write real skills under `root` ({name: body}) and load them for real."""
    for name, body in bodies.items():
        skill_dir = root / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\ndescription: {name} skill.\n---\n\n{body}\n", encoding="utf-8"
        )
    return Gate(SkillsLoader([root]).load())


# --- not a command -> unchanged --------------------------------------


@pytest.mark.parametrize(
    "prompt",
    [
        "hello",
        "",
        "  ",
        "\n",
        "what does /apple do?",  # a slash, but not at the start
    ],
)
def test_prompt_that_is_not_a_command_is_unchanged(gate, prompt):
    assert gate.parse_user_prompt(prompt) == prompt


# --- starts with "/" but names no skill -> unchanged -----------------


@pytest.mark.parametrize(
    "prompt",
    [
        "/banana",
        "/",
        "/etc/passwd please read this",
        "/Apple",  # names are case-sensitive: the folder is "apple"
    ],
)
def test_unknown_skill_leaves_the_prompt_unchanged(gate, prompt):
    assert gate.parse_user_prompt(prompt) == prompt


# --- a known skill -> its body ---------------------------------------


def test_known_skill_is_replaced_by_its_body(tmp_path):
    gate = gate_with_skills(tmp_path / "skills", {"apple": "Say blueberry."})

    assert gate.parse_user_prompt("/apple") == "Say blueberry."


# --- a preceding empty space is ignored -----------------------------------


def test_leading_space_is_ignored(tmp_path):
    gate = gate_with_skills(tmp_path / "skills", {"apple": "Say blueberry."})

    assert gate.parse_user_prompt(" /apple") == "Say blueberry."


# --- words after the name --------------------------------------------


def test_words_after_the_skill_name_are_ignored(tmp_path):
    gate = gate_with_skills(tmp_path / "skills", {"apple": "Say blueberry."})

    assert gate.parse_user_prompt("/apple please hurry") == "Say blueberry."


# --- only the invoked skill is loaded --------------------------------


def test_only_the_invoked_skills_body_is_returned(tmp_path):
    gate = gate_with_skills(
        tmp_path / "skills", {"apple": "Say blueberry.", "grape": "Say mango."}
    )

    result = gate.parse_user_prompt("/apple")

    assert "blueberry" in result
    assert "mango" not in result


# --- the exact text from the stage ------------------------------------


def test_body_keeps_its_inner_blank_line(tmp_path):
    body = (
        "Respond with exactly one word: blueberry\n\n"
        "Do not add any other text, punctuation, or formatting."
    )
    gate = gate_with_skills(tmp_path / "skills", {"apple": body})

    assert gate.parse_user_prompt("/apple") == body
