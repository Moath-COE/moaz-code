"""Tests for Gate: what the model sees in place of the raw user prompt.

API these tests pin down:

    Gate(skills_registry).parse_user_prompt(prompt: str).messages -> ParsedPrompt
    ParsedPrompt(messages: list[str], forked: Command | None = None)

The registry only needs `in`, get(name) and expand(name, rest) (see FakeRegistry below).

Rules:
    - "/<name>" (optionally followed by words) where <name> is a known skill
      -> [the skill's body with $ARGUMENTS / $N filled from the words after
         the name], and nothing else.
    - anything else -> [the prompt, unchanged].

`.messages` has one entry per user message the model should see. `.forked`
names a `context: fork` skill the user typed, for main to run in a subagent.

Work through the steps in order. Uncomment ONE step, watch it fail, then make
it pass. Do not uncomment the next step until the current one is green.
"""

from pathlib import Path

import pytest

from app.input.command import Command
from app.input.gate import Gate, ParsedPrompt
from app.skills import Skill, SkillRegistry, SkillsLoader
from app.skills.arguments import substitute_arguments
from tests.instructions import (
    HEADER_BODY_SEPARATOR,
    expected_header,
    expected_instructions,
)


class FakeRegistry:
    def __init__(self, bodies: dict[str, str], forked: frozenset[str] = frozenset()):
        self.bodies = bodies
        self.forked = forked

    def __contains__(self, name: str) -> bool:
        return name in self.bodies

    def get(self, name: str) -> Skill | None:
        if name not in self.bodies:
            return None
        return Skill(name, "d", Path(f"{name}/SKILL.md"), fork=name in self.forked)

    def expand(self, name: str, rest: str = "") -> str:
        return substitute_arguments(
            self.bodies[name], rest
        )  # KeyError if unknown, like the real one


def gate_with_skills(
    bodies: dict[str, str], forked: frozenset[str] = frozenset()
) -> Gate:
    return Gate(FakeRegistry(bodies, forked))


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
    assert gate.parse_user_prompt(prompt).messages == [prompt]


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
    assert gate.parse_user_prompt(prompt).messages == [prompt]


# --- a known skill -> its body ---------------------------------------


def test_known_skill_is_replaced_by_its_body():
    gate = gate_with_skills({"apple": "Say blueberry."})

    assert gate.parse_user_prompt("/apple").messages == ["Say blueberry."]


# --- a preceding empty space is ignored -----------------------------------


def test_leading_space_is_ignored():
    gate = gate_with_skills({"apple": "Say blueberry."})

    assert gate.parse_user_prompt(" /apple").messages == ["Say blueberry."]


# --- words after the name --------------------------------------------


def test_words_after_the_skill_name_are_ignored():
    gate = gate_with_skills({"apple": "Say blueberry."})

    assert gate.parse_user_prompt("/apple please hurry").messages == ["Say blueberry."]


# --- only the invoked skill is loaded --------------------------------


def test_only_the_invoked_skills_body_is_returned():
    gate = gate_with_skills({"apple": "Say blueberry.", "grape": "Say mango."})

    result = gate.parse_user_prompt("/apple").messages

    assert result == ["Say blueberry."]


# --- the exact text from the stage ------------------------------------


def test_body_keeps_its_inner_blank_line():
    body = (
        "Respond with exactly one word: blueberry\n\n"
        "Do not add any other text, punctuation, or formatting."
    )
    gate = gate_with_skills({"apple": body})

    assert gate.parse_user_prompt("/apple").messages == [body]


# --- arguments: what comes after the name fills the placeholders -----------


def test_arguments_placeholder_gets_everything_after_the_name():
    gate = gate_with_skills({"apple": "$ARGUMENTS"})

    assert gate.parse_user_prompt("/apple 4127").messages == ["4127"]


def test_positional_placeholders_get_single_words_in_the_order_the_body_asks():
    gate = gate_with_skills({"grape": "$1 $0"})

    assert gate.parse_user_prompt("/grape mango pear").messages == ["pear mango"]


def test_skill_invoked_without_arguments_gets_empty_strings():
    gate = gate_with_skills({"apple": "[$ARGUMENTS][$0]"})

    assert gate.parse_user_prompt("/apple").messages == ["[][]"]


def test_arguments_placeholder_keeps_the_original_spacing():
    # $ARGUMENTS is "everything after the name", not the words re-joined.
    gate = gate_with_skills({"apple": "$ARGUMENTS|$0|$1"})

    assert gate.parse_user_prompt("/apple a   b").messages == ["a   b|a|b"]


def test_leading_space_before_the_command_does_not_leak_into_arguments():
    gate = gate_with_skills({"apple": "[$ARGUMENTS]"})

    assert gate.parse_user_prompt("   /apple x").messages == ["[x]"]


def test_arguments_are_not_applied_to_an_unknown_skill():
    gate = gate_with_skills({"apple": "$ARGUMENTS"})

    assert gate.parse_user_prompt("/banana 4127").messages == ["/banana 4127"]


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
    assert stacked_gate.parse_user_prompt("/apple /grape 4127").messages == [
        "blueberry-4127",
        "cherry-4127",
    ]


def test_first_non_skill_token_ends_expansion_and_stays_in_the_arguments(
    stacked_gate,
):
    # "4127" ends the run, so the trailing "/grape" is plain argument text.
    assert stacked_gate.parse_user_prompt("/apple 4127 /grape").messages == [
        "blueberry-4127 /grape"
    ]


def test_unknown_skill_after_a_known_one_ends_expansion(stacked_gate):
    # There is no "pear" skill, so "/pear 4127" is all argument text.
    assert stacked_gate.parse_user_prompt("/apple /pear 4127").messages == [
        "blueberry-/pear 4127"
    ]


def test_stacked_skills_keep_the_order_of_the_prompt(stacked_gate):
    assert stacked_gate.parse_user_prompt("/grape /apple 1").messages == [
        "cherry-1",
        "blueberry-1",
    ]


def test_stacked_skills_without_arguments_get_empty_strings(stacked_gate):
    assert stacked_gate.parse_user_prompt("/apple /grape").messages == [
        "blueberry-",
        "cherry-",
    ]


def test_stacked_skills_share_positional_arguments():
    gate = gate_with_skills({"apple": "a:$0", "grape": "g:$1"})

    assert gate.parse_user_prompt("/apple /grape x y").messages == ["a:x", "g:y"]


def test_any_whitespace_can_separate_stacked_names_and_spacing_is_kept(stacked_gate):
    # Tabs/newlines separate names too, and $ARGUMENTS keeps its original spacing.
    assert stacked_gate.parse_user_prompt("/apple\n/grape\t a   b").messages == [
        "blueberry-a   b",
        "cherry-a   b",
    ]


def test_same_skill_named_twice_is_expanded_twice(stacked_gate):
    assert stacked_gate.parse_user_prompt("/apple /apple 1").messages == [
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

    expected = expected_instructions(tmp_path, "Run `scripts/checksum.sh`.")

    assert gate.parse_user_prompt("/apple").messages == [expected]


def test_arguments_are_filled_into_the_body_and_the_header_is_kept(tmp_path):
    gate = real_gate(tmp_path, "Checksum of $ARGUMENTS")

    [message] = gate.parse_user_prompt("/apple data.txt").messages

    assert message.startswith(expected_header(tmp_path))
    assert message.endswith(HEADER_BODY_SEPARATOR + "Checksum of data.txt")


# --- a forked skill ends a stacking run, as its last item ---------------------
#
# A `context: fork` skill must run in a subagent, never be expanded into the
# main conversation. Gate does not run it (it stays parse-only): it ends the
# run and reports it in `.forked`, with the text after it as its arguments.
# Normal skills before it get the same argument text.


@pytest.fixture
def forking_gate() -> Gate:
    return gate_with_skills(
        {"apple": "blueberry-$ARGUMENTS", "fork": "SECRET"}, forked=frozenset({"fork"})
    )


def test_forked_skill_alone_is_reported_with_its_arguments(forking_gate):
    assert forking_gate.parse_user_prompt("/fork 4127") == ParsedPrompt(
        messages=[], forked=Command("fork", "4127")
    )


def test_normal_skills_before_a_fork_get_the_text_after_it(forking_gate):
    assert forking_gate.parse_user_prompt("/apple /fork 4127") == ParsedPrompt(
        messages=["blueberry-4127"], forked=Command("fork", "4127")
    )


def test_forked_skill_ends_the_run_so_later_commands_are_its_arguments(
    forking_gate,
):
    assert forking_gate.parse_user_prompt("/fork /apple x") == ParsedPrompt(
        messages=[], forked=Command("fork", "/apple x")
    )


@pytest.mark.parametrize("prompt", ["hello", "/apple 4127", "/banana x"])
def test_nothing_forked_means_forked_is_none(forking_gate, prompt):
    assert forking_gate.parse_user_prompt(prompt).forked is None


def test_forked_skill_body_is_never_expanded_by_the_gate(forking_gate):
    result = forking_gate.parse_user_prompt("/apple /fork x")

    assert not any("SECRET" in message for message in result.messages)


def test_parsed_prompt_is_frozen():
    parsed = ParsedPrompt(messages=["x"])

    with pytest.raises(AttributeError):
        parsed.forked = Command("fork", "")  # type: ignore[misc]
