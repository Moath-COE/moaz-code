"""Test doubles for the agent loop.

They mimic only the slice of the OpenAI SDK that Agent actually touches:
    client.chat.completions.create(model=..., messages=..., tools=...)
    response.choices[0].message.content / .tool_calls
    tool_call.id / .function.name / .function.arguments (a JSON string)
"""

import json
from types import SimpleNamespace

from app.tools.base import Tool


def make_tool_call(call_id: str, name: str, arguments: dict | str) -> SimpleNamespace:
    """Build a fake tool call. Pass a str for `arguments` to simulate bad JSON."""
    raw = arguments if isinstance(arguments, str) else json.dumps(arguments)
    return SimpleNamespace(
        id=call_id, function=SimpleNamespace(name=name, arguments=raw)
    )


def make_response(content: str | None = None, tool_calls: list | None = None):
    """Build a fake chat-completion response with a single choice."""
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def make_empty_response():
    """A response with no choices at all."""
    return SimpleNamespace(choices=[])


class FakeClient:
    """Returns scripted responses in order and records every request.

    Usage:
        client = FakeClient([make_response(content="hi")])
        # ... run the agent ...
        client.calls[0]["messages"]   # what the agent sent on its first request
    """

    def __init__(self, responses: list):
        self._responses = list(responses)
        self.calls: list[dict] = []
        # Mirror the SDK's attribute path: client.chat.completions.create(...)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, *, model, messages, tools=None, **kwargs):
        # Snapshot the list: the agent keeps appending to the same one, so
        # storing the reference would make every recorded call show the final state.
        self.calls.append({"model": model, "messages": list(messages), "tools": tools})
        if not self._responses:
            raise AssertionError("FakeClient ran out of scripted responses")
        return self._responses.pop(0)


class FakeTool(Tool):
    """A stand-in tool so the registry is tested without any real tool.

    It returns a canned string and remembers how it was called.
    """

    def __init__(self, name: str = "Fake", output: str = "fake output"):
        super().__init__(
            name=name,
            description="a fake tool for tests",
            properties={"x": {"type": "string"}},
            required=["x"],
        )
        self.output = output
        self.calls: list[dict] = []

    def run(self, **kwargs) -> str:
        self.calls.append(kwargs)
        return self.output


class FakeSpawner:
    """Stands in for SubagentRunner: records each spec and returns a canned answer.

    Pass `error` to make every run raise it instead.
    """

    def __init__(self, answer: str = "blueberry", error: Exception | None = None):
        self.answer = answer
        self.error = error
        self.specs: list = []

    def run(self, spec) -> str:
        self.specs.append(spec)
        if self.error is not None:
            raise self.error
        return self.answer
