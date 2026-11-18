import time

import pytest

from app.tools.bash import BashTool


@pytest.fixture
def bash_tool() -> BashTool:
    return BashTool()


def test_schema_declares_command_as_required(bash_tool):
    schema = bash_tool.schema()

    assert schema["function"]["name"] == "Bash"
    assert "command" in schema["function"]["parameters"]["properties"]
    assert schema["function"]["parameters"]["required"] == ["command"]


# --- Output format -----------------------------------------------------------


def test_returns_stdout(bash_tool):
    result = bash_tool.run(command="echo hello")

    assert result == "stdout: hello"


def test_returns_stderr(bash_tool):
    result = bash_tool.run(command="echo oops >&2")

    assert result == "stderr: oops"


def test_returns_both_streams_when_both_are_written(bash_tool):
    result = bash_tool.run(command="echo out; echo err >&2")

    assert "stdout: out" in result
    assert "stderr: err" in result


def test_stdout_only_command_does_not_mention_stderr(bash_tool):
    result = bash_tool.run(command="echo hello")

    assert "stderr:" not in result


def test_silent_command_says_there_was_no_output(bash_tool):
    result = bash_tool.run(command="true")

    assert result == "(no output)"


# --- Exit codes --------------------------------------------------------------


def test_nonzero_exit_code_is_reported_but_is_not_a_tool_error(bash_tool):
    result = bash_tool.run(command="exit 3")

    assert "exit code: 3" in result.lower()
    assert not result.startswith("Error")


def test_successful_command_does_not_mention_an_exit_code(bash_tool):
    result = bash_tool.run(command="echo hello")

    assert "exit code:" not in result.lower()


# --- Shell features ----------------------------------------------------------


def test_shell_pipes_work(bash_tool):
    result = bash_tool.run(command="echo a | tr a b")

    assert result == "stdout: b"


def test_shell_and_operator_works(bash_tool):
    result = bash_tool.run(command="echo one && echo two")

    assert "one" in result
    assert "two" in result


def test_runs_commands_with_bash_not_plain_sh(bash_tool):
    # Brace expansion is a bashism: dash (/bin/sh on Debian and Ubuntu) would
    # print the literal "{a,b}". The tool is called Bash, so it must be bash.
    result = bash_tool.run(command="echo {a,b}")

    assert result == "stdout: a b"


# --- Timeout and stdin -------------------------------------------------------


def test_timeout_returns_an_error_string_promptly():
    tool = BashTool(timeout=0.2)

    start = time.monotonic()
    result = tool.run(command="sleep 5; echo done")
    elapsed = time.monotonic() - start

    assert result.startswith("Error")
    assert "timed out" in result.lower()
    assert "stdout:" not in result  # the command's own output never came back
    assert elapsed < 2


def test_command_that_reads_stdin_does_not_hang():
    tool = BashTool(timeout=2)

    result = tool.run(command="cat")

    assert "timed out" not in result.lower()


# --- Empty command -----------------------------------------------------------


def test_empty_command_returns_an_error_string(bash_tool):
    result = bash_tool.run(command="")

    assert "error" in result.lower()


# --- Output truncation -------------------------------------------------------


def test_long_stdout_is_truncated_with_a_notice():
    tool = BashTool(max_output_chars=100)

    result = tool.run(command="head -c 10000 /dev/zero | tr '\\0' x")

    assert len(result) < 300
    assert "truncated" in result.lower()
    assert "9900" in result  # tells the model how much was dropped


def test_long_stderr_is_truncated_with_a_notice():
    tool = BashTool(max_output_chars=100)

    result = tool.run(command="head -c 10000 /dev/zero | tr '\\0' x >&2")

    assert len(result) < 300
    assert result.startswith("stderr:")
    assert "truncated" in result.lower()


def test_output_exactly_at_the_limit_is_not_truncated():
    tool = BashTool(max_output_chars=5)

    result = tool.run(command="printf hello")

    assert result == "stdout: hello"


def test_exit_code_survives_truncation():
    tool = BashTool(max_output_chars=100)

    result = tool.run(command="head -c 10000 /dev/zero | tr '\\0' x; exit 3")

    assert "truncated" in result.lower()
    assert "exit code: 3" in result
