import pytest

from app.agent import Agent
from app.tools.registry import ToolRegistry
from tests.fakes import (
    FakeClient,
    FakeTool,
    make_empty_response,
    make_response,
    make_tool_call,
)


@pytest.fixture
def registry() -> ToolRegistry:
    return ToolRegistry()


def make_agent(client: FakeClient, registry: ToolRegistry, **overrides) -> Agent:
    """One place to build an Agent, so a constructor change touches one line."""
    return Agent(
        client=client,
        registry=registry,
        model="test-model",
        **overrides,
    )


def test_returns_content_when_model_answers_without_tool_calls(registry):
    client = FakeClient([make_response(content="the answer")])
    agent = make_agent(client, registry)

    result = agent.run("what is 2+2?")

    assert result == "the answer"
    assert len(client.calls) == 1
    assert client.calls[0]["messages"][0] == {"role": "user", "content": "what is 2+2?"}


# --- TODO (yours), in this order. Write each test, watch it fail, then code. --


def test_tool_result_is_sent_back_to_the_model(registry):
    tool = FakeTool(name="Fake", output="tool output")
    registry.register(tool)

    client = FakeClient(
        [
            make_response(
                tool_calls=[
                    make_tool_call(name="Fake", arguments='{"x": "1"}', call_id="call1")
                ]
            ),
            make_response(content="final answer"),
        ]
    )
    agent = make_agent(client, registry)

    result = agent.run("call the tool")

    assert result == "final answer"
    assert len(client.calls) == 2
    assert {
        "role": "tool",
        "tool_call_id": "call1",
        "content": "tool output",
    } in client.calls[1]["messages"]


def test_unknown_tool_error_is_sent_back_and_loop_continues(registry):
    client = FakeClient(
        [
            make_response(
                tool_calls=[
                    make_tool_call(name="Nope", arguments='{"x": "1"}', call_id="call1")
                ]
            ),
            make_response(content="final answer"),
        ]
    )
    agent = make_agent(client, registry)

    agent.run("call the unknown tool")

    tool_messages = [
        m
        for m in client.calls[1]["messages"]
        if isinstance(m, dict) and m.get("role") == "tool"
    ]

    assert len(tool_messages) == 1
    assert tool_messages[0]["tool_call_id"] == "call1"
    assert "Nope" in tool_messages[0]["content"]


def test_malformed_json_arguments_are_reported_to_the_model(registry):
    tool = FakeTool(name="Fake", output="tool output")
    registry.register(tool)

    client = FakeClient(
        [
            make_response(
                tool_calls=[
                    make_tool_call(name="Fake", arguments="{not json", call_id="call1")
                ]
            ),
            make_response(content="final answer"),
        ]
    )
    agent = make_agent(client, registry)

    agent.run("call the tool with malformed JSON")

    tool_messages = [
        m
        for m in client.calls[1]["messages"]
        if isinstance(m, dict) and m.get("role") == "tool"
    ]

    assert len(tool_messages) == 1
    assert tool_messages[0]["tool_call_id"] == "call1"
    assert "JSONDecodeError" in tool_messages[0]["content"]


def test_multiple_tool_calls_in_one_reply_are_all_executed_in_order(registry):
    tool1 = FakeTool(name="Tool1", output="output1")
    tool2 = FakeTool(name="Tool2", output="output2")
    registry.register(tool1)
    registry.register(tool2)

    client = FakeClient(
        [
            make_response(
                tool_calls=[
                    make_tool_call(
                        name="Tool1", arguments='{"x": "1"}', call_id="call1"
                    ),
                    make_tool_call(
                        name="Tool2", arguments='{"x": "2"}', call_id="call2"
                    ),
                ]
            ),
            make_response(content="final answer"),
        ]
    )
    agent = make_agent(client, registry)

    result = agent.run("call both tools")

    assert result == "final answer"
    assert len(client.calls) == 2

    tool_messages = [
        m
        for m in client.calls[1]["messages"]
        if isinstance(m, dict) and m.get("role") == "tool"
    ]

    assert len(tool_messages) == 2
    assert tool_messages[0]["tool_call_id"] == "call1"
    assert tool_messages[0]["content"] == "output1"
    assert tool_messages[1]["tool_call_id"] == "call2"
    assert tool_messages[1]["content"] == "output2"


def test_no_choices_raises_runtime_error(registry):
    client = FakeClient([make_empty_response()])
    agent = make_agent(client, registry)

    with pytest.raises(RuntimeError, match="no choices in response"):
        agent.run("trigger no choices")


def test_max_iterations_limit(registry):
    tool = FakeTool(name="Fake", output="tool output")
    registry.register(tool)

    # Script the model to always ask for a tool call, so we hit the max iterations.
    client = FakeClient(
        [
            make_response(
                tool_calls=[
                    make_tool_call(name="Fake", arguments='{"x": "1"}', call_id="call1")
                ]
            )
        ]
        * 5  # More than max_iterations to ensure we hit the limit
    )
    agent = make_agent(client, registry, max_iterations=3)

    with pytest.raises(RuntimeError, match="max iterations reached"):
        agent.run("call the tool repeatedly")

    assert len(client.calls) == 3  # Should only call the client max_iterations times
