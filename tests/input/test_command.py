"""Tests for parse_command: the pure, lexical half of the Gate.

API these tests pin down (app/input/command.py):

    parse_command(text: str) -> Command | None
    Command(name: str, rest: str)        # frozen dataclass

A command is "/<name>" at the start of the text (leading whitespace allowed).
`rest` is everything after the name and the whitespace that follows it.

The parser knows NOTHING about skills: it never asks "does this skill exist?".
That is the Gate's job. So no registry, no tmp_path, no fakes in this file.

Work through the steps in order. Uncomment ONE step, watch it fail, then make
it pass. Do not uncomment the next step until the current one is green.
"""

import pytest

from app.input.command import Command, parse_command

# --- Step 1: text that is not a command -> None ---------------------------
# (Start here: create app/input/command.py with Command + a parse_command
#  that returns None, and see which tests already pass for the wrong reason.)


@pytest.mark.parametrize(
    "text",
    [
        "hello",
        "",
        "  ",
        "\n",
        "what does /apple do?",  # a slash, but not at the start
        "/",  # a slash with no name after it
    ],
)
def test_text_that_is_not_a_command_returns_none(text):
    assert parse_command(text) is None


# --- Step 2: a bare command -> its name, empty rest -----------------------


def test_bare_command_has_a_name_and_an_empty_rest():
    assert parse_command("/apple") == Command(name="apple", rest="")


# --- Step 3: leading whitespace is ignored --------------------------------


@pytest.mark.parametrize("text", [" /apple", "   /apple", "\n/apple", "\t/apple"])
def test_leading_whitespace_before_the_slash_is_ignored(text):
    assert parse_command(text) == Command(name="apple", rest="")


# --- Step 4: everything after the name is the rest ------------------------


def test_text_after_the_name_becomes_the_rest():
    assert parse_command("/apple 4127") == Command(name="apple", rest="4127")


def test_whitespace_between_name_and_rest_is_not_part_of_the_rest():
    assert parse_command("/apple    4127") == Command(name="apple", rest="4127")


def test_leading_whitespace_does_not_leak_into_the_rest():
    assert parse_command("   /apple x") == Command(name="apple", rest="x")


# --- Step 5: the rest keeps its original shape ----------------------------


def test_rest_keeps_the_original_inner_spacing():
    assert parse_command("/apple a   b") == Command(name="apple", rest="a   b")


def test_rest_can_span_several_lines():
    assert parse_command("/apple one\ntwo") == Command(name="apple", rest="one\ntwo")


# --- Step 6: any whitespace separates the name from the rest --------------
# This is what makes stacking work later: the Gate calls parse_command again
# on `rest`, so a second "/name" must come back untouched.


def test_a_newline_or_tab_can_separate_the_name_from_the_rest():
    assert parse_command("/apple\n/grape\t a   b") == Command(
        name="apple", rest="/grape\t a   b"
    )


def test_parsing_the_rest_again_finds_the_next_command():
    first = parse_command("/apple /grape 4127")

    assert first == Command(name="apple", rest="/grape 4127")
    assert parse_command(first.rest) == Command(name="grape", rest="4127")


# --- Step 7: the parser does not judge the name ---------------------------
# Whether "Apple" or "etc/passwd" is a real skill is the Gate's question.


def test_name_keeps_its_case():
    assert parse_command("/Apple") == Command(name="Apple", rest="")


def test_name_is_everything_up_to_the_first_whitespace():
    assert parse_command("/etc/passwd please") == Command(
        name="etc/passwd", rest="please"
    )


# --- Step 8: Command is a value object ------------------------------------


def test_command_is_immutable():
    command = Command(name="apple", rest="")

    with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
        command.name = "grape"
