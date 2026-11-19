"""Tests for Gate: what the model sees in place of the raw user prompt.

API these tests pin down:

    Gate(registry)  # needs only registry.get_body(name) -> str | None.parse_user_prompt(prompt: str) -> str

Rules:
    - "/<name>" (optionally followed by words) where <name> is a known skill
      -> the skill's body, and nothing else.
    - anything else -> the prompt, unchanged.

Work through the steps in order. Uncomment ONE step, watch it fail, then make
it pass. Do not uncomment the next step until the current one is green.
"""

import pytest

from app.input.gate import Gate


class FakeRegistry:
    """Stands in for SkillRegistry: bodies come from a dict, no files involved."""

    def __init__(self, bodies: dict[str, str]):
        self.bodies = bodies

    def get_body(self, name: str) -> str | None:
        return self.bodies.get(name)


def gate_with_skills(bodies: dict[str, str]) -> Gate:
    return Gate(FakeRegistry(bodies))


@pytest.fixture
def gate() -> Gate:
    return gate_with_skills({"apple": "Say blueberry."})


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


def test_known_skill_is_replaced_by_its_body():
    gate = gate_with_skills({"apple": "Say blueberry."})

    assert gate.parse_user_prompt("/apple") == "Say blueberry."


# --- a preceding empty space is ignored -----------------------------------


def test_leading_space_is_ignored():
    gate = gate_with_skills({"apple": "Say blueberry."})

    assert gate.parse_user_prompt(" /apple") == "Say blueberry."


# --- words after the name --------------------------------------------


def test_words_after_the_skill_name_are_ignored():
    gate = gate_with_skills({"apple": "Say blueberry."})

    assert gate.parse_user_prompt("/apple please hurry") == "Say blueberry."


# --- only the invoked skill is loaded --------------------------------


def test_only_the_invoked_skills_body_is_returned():
    gate = gate_with_skills({"apple": "Say blueberry.", "grape": "Say mango."})

    result = gate.parse_user_prompt("/apple")

    assert "blueberry" in result
    assert "mango" not in result


# --- the exact text from the stage ------------------------------------


def test_body_keeps_its_inner_blank_line():
    body = (
        "Respond with exactly one word: blueberry\n\n"
        "Do not add any other text, punctuation, or formatting."
    )
    gate = gate_with_skills({"apple": body})

    assert gate.parse_user_prompt("/apple") == body
