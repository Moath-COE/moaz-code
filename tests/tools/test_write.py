import pytest

from app.tools.write import WriteTool


@pytest.fixture
def write_tool() -> WriteTool:
    return WriteTool()


def test_schema_declares_file_path_and_content_as_required(write_tool):
    schema = write_tool.schema()

    assert schema["function"]["name"] == "Write"
    properties = schema["function"]["parameters"]["properties"]
    assert "file_path" in properties
    assert "content" in properties
    assert schema["function"]["parameters"]["required"] == ["file_path", "content"]


def test_writes_content_to_a_new_file(write_tool, tmp_path):
    file = tmp_path / "hello.txt"

    write_tool.run(file_path=str(file), content="hello world")

    # Assert on the disk, not just the return value: that's the real behavior.
    assert file.read_text(encoding="utf-8") == "hello world"


def test_success_message_mentions_the_path(write_tool, tmp_path):
    file = tmp_path / "hello.txt"

    result = write_tool.run(file_path=str(file), content="hi")

    assert not result.startswith("Error")
    assert str(file) in result


def test_overwrites_existing_file(write_tool, tmp_path):
    file = tmp_path / "hello.txt"
    file.write_text("old content that is longer", encoding="utf-8")

    write_tool.run(file_path=str(file), content="new")

    # "new" alone proves truncation: append mode would leave the old text behind.
    assert file.read_text(encoding="utf-8") == "new"


def test_empty_content_creates_an_empty_file(write_tool, tmp_path):
    file = tmp_path / "empty.txt"

    result = write_tool.run(file_path=str(file), content="")

    assert not result.startswith("Error")
    assert file.exists()
    assert file.read_text(encoding="utf-8") == ""


def test_preserves_multiline_and_unicode_content(write_tool, tmp_path):
    file = tmp_path / "text.txt"
    content = "line one\nline two\nçafé ✓\n"

    write_tool.run(file_path=str(file), content=content)

    assert file.read_text(encoding="utf-8") == content


def test_missing_parent_directory_returns_error_string(write_tool, tmp_path):
    file = tmp_path / "no_such_dir" / "hello.txt"

    result = write_tool.run(file_path=str(file), content="hi")

    assert result.startswith("Error")
    assert not file.parent.exists()  # documents the decision: we don't mkdir


def test_directory_path_returns_error_string(write_tool, tmp_path):
    result = write_tool.run(file_path=str(tmp_path), content="hi")

    assert result.startswith("Error")
