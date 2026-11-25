"""Tests for SubagentRunner: one run of the agent loop in a fresh conversation.

API these tests pin down:

    SubagentSpec(prompt: str, label: str, system_prompt: str | None = None)
    SubagentRunner(client, model, registry, max_iterations=30)
    .run(spec) -> str      the subagent's final answer; raises on failure
"""

import pytest

from app.subagent import SubagentRunner, SubagentSpec
from app.tools.registry import ToolRegistry
from tests.fakes import FakeClient, FakeTool, make_response, make_tool_call


def make_runner(client: FakeClient, registry: ToolRegistry | None = None, **kw):
    return SubagentRunner(
        client=client, model="test-model", registry=registry or ToolRegistry(), **kw
    )


def test_subagent_conversation_holds_only_the_prompt():
    # The tester's first check: the body alone, no system prompt, no question.
    client = FakeClient([make_response(content="blueberry")])

    make_runner(client).run(
        SubagentSpec(prompt="Respond with exactly one word: blueberry", label="x")
    )

    assert client.calls[0]["messages"] == [
        {"role": "user", "content": "Respond with exactly one word: blueberry"}
    ]


def test_run_returns_the_subagent_final_answer():
    client = FakeClient([make_response(content="blueberry")])

    answer = make_runner(client).run(SubagentSpec(prompt="say it", label="x"))

    assert answer == "blueberry"


def test_system_prompt_is_sent_when_the_spec_has_one():
    client = FakeClient([make_response(content="ok")])

    make_runner(client).run(
        SubagentSpec(prompt="task", label="x", system_prompt="You are a subagent.")
    )

    assert client.calls[0]["messages"][0] == {
        "role": "system",
        "content": "You are a subagent.",
    }


def test_each_run_starts_a_new_conversation():
    client = FakeClient([make_response(content="one"), make_response(content="two")])
    runner = make_runner(client)

    runner.run(SubagentSpec(prompt="first", label="a"))
    runner.run(SubagentSpec(prompt="second", label="b"))

    assert client.calls[1]["messages"] == [{"role": "user", "content": "second"}]


def test_subagent_can_use_the_tools_it_was_given():
    tool = FakeTool(name="Fake", output="tool output")
    registry = ToolRegistry()
    registry.register(tool)
    client = FakeClient(
        [
            make_response(tool_calls=[make_tool_call("c1", "Fake", {"x": "1"})]),
            make_response(content="done"),
        ]
    )

    answer = make_runner(client, registry).run(SubagentSpec(prompt="go", label="x"))

    assert answer == "done"
    assert tool.calls == [{"x": "1"}]
    assert client.calls[0]["tools"] == registry.tools


def test_failure_is_raised_not_turned_into_text():
    # Turning errors into text for the model is the calling tool's job.
    client = FakeClient([make_response(tool_calls=[make_tool_call("c", "Nope", {})])])

    with pytest.raises(RuntimeError, match="max iterations"):
        make_runner(client, max_iterations=1).run(SubagentSpec(prompt="go", label="x"))
