"""Tests for Gate: what the model sees in place of the raw user prompt.

API these tests pin down:

    Gate(registry).parse_user_prompt(prompt: str) -> list[str]

The registry only needs get_instructions(name) -> str | None (see FakeRegistry below).

Rules:
    - "/<name>" (optionally followed by words) where <name> is a known skill
      -> [the skill's body with $ARGUMENTS / $N filled from the words after
         the name], and nothing else.
    - anything else -> [the prompt, unchanged].

The result is a list: one entry per user message the model should see.

Work through the steps in order. Uncomment ONE step, watch it fail, then make
it pass. Do not uncomment the next step until the current one is green.
"""

import pytest

from app.input.gate import Gate
from app.skills import SkillRegistry, SkillsLoader


class FakeRegistry:
    """Stands in for SkillRegistry: bodies come from a dict, no files involved."""

    def __init__(self, bodies: dict[str, str]):
        self.bodies = bodies

    def get_instructions(self, name: str) -> str | None:
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
    assert gate.parse_user_prompt(prompt) == [prompt]


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
    assert gate.parse_user_prompt(prompt) == [prompt]


# --- a known skill -> its body ---------------------------------------


def test_known_skill_is_replaced_by_its_body():
    gate = gate_with_skills({"apple": "Say blueberry."})

    assert gate.parse_user_prompt("/apple") == ["Say blueberry."]


# --- a preceding empty space is ignored -----------------------------------


def test_leading_space_is_ignored():
    gate = gate_with_skills({"apple": "Say blueberry."})

    assert gate.parse_user_prompt(" /apple") == ["Say blueberry."]


# --- words after the name --------------------------------------------


def test_words_after_the_skill_name_are_ignored():
    gate = gate_with_skills({"apple": "Say blueberry."})

    assert gate.parse_user_prompt("/apple please hurry") == ["Say blueberry."]


# --- only the invoked skill is loaded --------------------------------


def test_only_the_invoked_skills_body_is_returned():
    gate = gate_with_skills({"apple": "Say blueberry.", "grape": "Say mango."})

    result = gate.parse_user_prompt("/apple")

    assert result == ["Say blueberry."]


# --- the exact text from the stage ------------------------------------


def test_body_keeps_its_inner_blank_line():
    body = (
        "Respond with exactly one word: blueberry\n\n"
        "Do not add any other text, punctuation, or formatting."
    )
    gate = gate_with_skills({"apple": body})

    assert gate.parse_user_prompt("/apple") == [body]


# --- arguments: what comes after the name fills the placeholders -----------


def test_arguments_placeholder_gets_everything_after_the_name():
    gate = gate_with_skills({"apple": "$ARGUMENTS"})

    assert gate.parse_user_prompt("/apple 4127") == ["4127"]


def test_positional_placeholders_get_single_words_in_the_order_the_body_asks():
    gate = gate_with_skills({"grape": "$1 $0"})

    assert gate.parse_user_prompt("/grape mango pear") == ["pear mango"]


def test_skill_invoked_without_arguments_gets_empty_strings():
    gate = gate_with_skills({"apple": "[$ARGUMENTS][$0]"})

    assert gate.parse_user_prompt("/apple") == ["[][]"]


def test_arguments_placeholder_keeps_the_original_spacing():
    # $ARGUMENTS is "everything after the name", not the words re-joined.
    gate = gate_with_skills({"apple": "$ARGUMENTS|$0|$1"})

    assert gate.parse_user_prompt("/apple a   b") == ["a   b|a|b"]


def test_leading_space_before_the_command_does_not_leak_into_arguments():
    gate = gate_with_skills({"apple": "[$ARGUMENTS]"})

    assert gate.parse_user_prompt("   /apple x") == ["[x]"]


def test_arguments_are_not_applied_to_an_unknown_skill():
    gate = gate_with_skills({"apple": "$ARGUMENTS"})

    assert gate.parse_user_prompt("/banana 4127") == ["/banana 4127"]


# --- stacking: several skills at the start of one prompt -----------------
#
# Expansion runs from the start. Every token naming a skill is expanded; the
# first token that doesn't ends the run, and it plus everything after it is
# the argument text shared by every expanded skill.


@pytest.fixture
def stacked_gate() -> Gate:
    return gate_with_skills(
        {"apple": "blueberry-$ARGUMENTS", "grape": "cherry-$ARGUMENTS"}
    )


def test_stacked_skills_each_become_their_own_message_with_shared_arguments(
    stacked_gate,
):
    assert stacked_gate.parse_user_prompt("/apple /grape 4127") == [
        "blueberry-4127",
        "cherry-4127",
    ]


def test_first_non_skill_token_ends_expansion_and_stays_in_the_arguments(
    stacked_gate,
):
    # "4127" ends the run, so the trailing "/grape" is plain argument text.
    assert stacked_gate.parse_user_prompt("/apple 4127 /grape") == [
        "blueberry-4127 /grape"
    ]


def test_unknown_skill_after_a_known_one_ends_expansion(stacked_gate):
    # There is no "pear" skill, so "/pear 4127" is all argument text.
    assert stacked_gate.parse_user_prompt("/apple /pear 4127") == [
        "blueberry-/pear 4127"
    ]


def test_stacked_skills_keep_the_order_of_the_prompt(stacked_gate):
    assert stacked_gate.parse_user_prompt("/grape /apple 1") == [
        "cherry-1",
        "blueberry-1",
    ]


def test_stacked_skills_without_arguments_get_empty_strings(stacked_gate):
    assert stacked_gate.parse_user_prompt("/apple /grape") == [
        "blueberry-",
        "cherry-",
    ]


def test_stacked_skills_share_positional_arguments():
    gate = gate_with_skills({"apple": "a:$0", "grape": "g:$1"})

    assert gate.parse_user_prompt("/apple /grape x y") == ["a:x", "g:y"]


def test_any_whitespace_can_separate_stacked_names_and_spacing_is_kept(stacked_gate):
    # Tabs/newlines separate names too, and $ARGUMENTS keeps its original spacing.
    assert stacked_gate.parse_user_prompt("/apple\n/grape\t a   b") == [
        "blueberry-a   b",
        "cherry-a   b",
    ]


def test_same_skill_named_twice_is_expanded_twice(stacked_gate):
    assert stacked_gate.parse_user_prompt("/apple /apple 1") == [
        "blueberry-1",
        "blueberry-1",
    ]


# --- the folder header (disclosure level 3) ---------------------------------
#
# These use the real SkillRegistry (files in tmp_path) instead of FakeRegistry:
# the point is how Gate and the registry's header work TOGETHER.


def real_gate(tmp_path, body: str) -> Gate:
    skill_dir = tmp_path / "apple"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        f"---\ndescription: Does things.\n---\n\n{body}\n", encoding="utf-8"
    )
    return Gate(SkillRegistry(SkillsLoader([tmp_path]).load()))


def test_invoked_skill_message_names_the_skill_folder_and_keeps_the_body(tmp_path):
    gate = real_gate(tmp_path, "Run `scripts/checksum.sh`.")

    expected = (
        f"Skill: apple (located at {tmp_path / 'apple'})\n"
        "Paths in the instructions below are relative to that folder.\n"
        "\n"
        "Run `scripts/checksum.sh`."
    )

    assert gate.parse_user_prompt("/apple") == [expected]


def test_arguments_are_filled_into_the_body_and_the_header_is_kept(tmp_path):
    gate = real_gate(tmp_path, "Checksum of $ARGUMENTS")

    [message] = gate.parse_user_prompt("/apple data.txt")

    assert message.startswith(f"Skill: apple (located at {tmp_path / 'apple'})\n")
    assert message.endswith("\n\nChecksum of data.txt")
