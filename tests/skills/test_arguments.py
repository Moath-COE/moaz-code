"""Tests for skill argument substitution.

API these tests pin down:

    substitute_arguments(body: str, arguments: str) -> str   # in app/skills/arguments.py

It is a PURE function: no files, no Skill, no Gate. Gate will call it later.

Work through the steps in order. Uncomment ONE step, watch it fail, then make
it pass. Do not uncomment the next step until the current one is green.
"""

import pytest

from app.skills.arguments import substitute_arguments


# --- Step 1: $ARGUMENTS is the whole string ---------------------------------
# One reason to fail: whole-string substitution. Nothing positional yet.
def test_arguments_placeholder_is_replaced_with_the_full_string():
    assert substitute_arguments("$ARGUMENTS", "staging eu-west") == "staging eu-west"


# --- Step 2: $0, $1 are single words, in the order the BODY asks for --------
# def test_dollar_n_is_replaced_by_the_nth_word():
#     assert substitute_arguments("$1 $0", "mango pear") == "pear mango"


# --- Step 3: a placeholder may appear more than once, and with surrounding text
# def test_same_placeholder_can_repeat():
#     assert substitute_arguments("$0 and $0 again", "a") == "a and a again"
#
#
# def test_text_around_placeholders_is_untouched():
#     body = "Deploy to $0 in region $1. Full request was: $ARGUMENTS"
#     expected = "Deploy to staging in region eu-west. Full request was: staging eu-west"
#     assert substitute_arguments(body, "staging eu-west") == expected


# --- Step 4: missing arguments become empty strings -------------------------
# def test_no_arguments_replaces_every_placeholder_with_empty_string():
#     assert substitute_arguments("x $ARGUMENTS $0 y", "") == "x   y"
#
#
# def test_out_of_range_index_becomes_empty_string():
#     assert substitute_arguments("[$0][$5]", "a") == "[a][]"


# --- Step 5: splitting is on any whitespace; $ARGUMENTS keeps the original --
# def test_arguments_are_split_on_any_whitespace():
#     assert substitute_arguments("$0|$1", "a \t b\n") == "a|b"


# --- Step 6: $ARGUMENTS[N] -- the ordering trap ------------------------------
# If you replace "$ARGUMENTS" first, "$ARGUMENTS[0]" becomes "a b[0]".
# @pytest.mark.parametrize(
#     "body, arguments, expected",
#     [
#         ("$ARGUMENTS[1]", "a b", "b"),
#         ("$ARGUMENTS[0] / $ARGUMENTS", "a b", "a / a b"),
#         ("$ARGUMENTS / $ARGUMENTS[0]", "a b", "a b / a"),
#         ("$ARGUMENTS[9]", "a", ""),
#     ],
# )
# def test_bracket_form_selects_one_argument(body, arguments, expected):
#     assert substitute_arguments(body, arguments) == expected


# --- Step 7: $10 is the eleventh word, not "$1" followed by "0" -------------
# def test_multi_digit_index_is_read_greedily():
#     words = " ".join(f"w{i}" for i in range(11))
#     assert substitute_arguments("$10 $1", words) == "w10 w1"


# --- Step 8: substituted text is never re-scanned ---------------------------
# An argument that LOOKS like a placeholder must come through literally.
# (Falls out for free with a single re.sub pass; fails with chained replaces.)
# def test_substituted_values_are_not_substituted_again():
#     assert substitute_arguments("$0 $1", "$1 x") == "$1 x"
