"""Tests for parse_body: the text after the frontmatter.

Step 0 of the gate work. The gate sends this text to the model, so its exact
shape matters (the CodeCrafters tester compares the model's answer to it).
"""

from app.skills.parse_yaml import parse_body


def test_returns_the_text_after_the_frontmatter():
    text = "---\ndescription: x\n---\nDo the thing.\n"

    assert parse_body(text) == "Do the thing."


def test_surrounding_blank_lines_are_stripped():
    text = "---\ndescription: x\n---\n\n\nDo the thing.\n\n"

    assert parse_body(text) == "Do the thing."


def test_blank_lines_inside_the_body_are_kept():
    text = "---\ndescription: x\n---\nLine one.\n\nLine two.\n"

    assert parse_body(text) == "Line one.\n\nLine two."


def test_dashes_inside_the_body_do_not_cut_it():
    text = "---\ndescription: x\n---\nFirst.\n\n---\n\nSecond.\n"

    assert parse_body(text) == "First.\n\n---\n\nSecond."


def test_text_without_frontmatter_is_returned_whole():
    assert parse_body("just a body\n") == "just a body"


def test_frontmatter_that_never_closes_returns_the_whole_text():
    text = "---\ndescription: x\nno closing marker\n"

    assert parse_body(text) == text.strip()
