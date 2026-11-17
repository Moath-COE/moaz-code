import pytest

from app.tools.read import ReadTool


@pytest.fixture
def read_tool() -> ReadTool:
    return ReadTool()


def test_schema_declares_file_path_as_required(read_tool):
    schema = read_tool.schema()

    assert schema["function"]["name"] == "Read"
    assert "file_path" in schema["function"]["parameters"]["properties"]
    assert schema["function"]["parameters"]["required"] == ["file_path"]


def test_returns_file_contents(read_tool, tmp_path):
    file = tmp_path / "hello.txt"
    file.write_text("hello world", encoding="utf-8")

    result = read_tool.run(file_path=str(file))

    assert result == "hello world"


def test_missing_file_returns_error_string(read_tool, tmp_path):
    missing = tmp_path / "nope.txt"

    result = read_tool.run(file_path=str(missing))

    assert result.startswith("Error")


def test_directory_returns_error_string(read_tool, tmp_path):
    result = read_tool.run(file_path=str(tmp_path))

    assert result.startswith("Error")


def test_binary_file_returns_error_string(read_tool, tmp_path):
    binary = tmp_path / "blob.bin"
    binary.write_bytes(b"\xff\xfe\x00\x80")

    result = read_tool.run(file_path=str(binary))

    assert result.startswith("Error")
