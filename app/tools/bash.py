import subprocess

from .base import Tool


class BashTool(Tool):
    """A tool that executes bash commands and returns the structured output."""

    def __init__(self, timeout: float = 30, max_output_chars: int = 10000):
        super().__init__(
            name="Bash",
            description="Execute a bash command and return the output",
            properties={
                "command": {
                    "type": "string",
                    "description": "The bash command to execute",
                }
            },
            required=["command"],
        )
        self.timeout = timeout
        self.max_output_chars = max_output_chars

    def _truncate(self, text: str) -> str:
        if len(text) <= self.max_output_chars:
            return text
        omitted = len(text) - self.max_output_chars
        return text[: self.max_output_chars] + f"\n... [truncated {omitted} characters]"

    def run(self, command: str) -> str:  # pyright: ignore[reportIncompatibleMethodOverride]
        if not command.strip():
            return "Error: command is empty"
        try:
            result = subprocess.run(
                command,
                shell=True,
                executable="/bin/bash",
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired:
            return f"Error: {command} timed out after {self.timeout} seconds"
        else:
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            parts = []
            if stdout:
                parts.append(f"stdout: {self._truncate(stdout)}")
            if stderr:
                parts.append(f"stderr: {self._truncate(stderr)}")
            if result.returncode != 0:
                parts.append(f"exit code: {result.returncode}")
            return "\n".join(parts) or "(no output)"
