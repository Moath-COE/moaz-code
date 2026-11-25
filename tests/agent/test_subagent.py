"""Tests for SubagentRunner: one run of the agent loop in a fresh conversation.

API these tests pin down:

    SubagentSpec(prompt: str, label: str, system_prompt: str | None = None)
    SubagentRunner(client, model, build_tools, max_iterations=30,
                   max_depth=1, depth=0)
    .can_spawn -> bool     depth < max_depth
    .run(spec) -> str      the subagent's final answer; raises on failure,
                           SpawnNotAllowed when can_spawn is False

build_tools(spawner) -> ToolRegistry gives the child its tools. The spawner it
receives is a runner one level deeper, so the depth rule lives in one place.
"""

import pytest

from app.agent import SpawnNotAllowed, SubagentRunner, SubagentSpec
from app.tools.registry import ToolRegistry
from tests.fakes import FakeClient, FakeTool, make_response, make_tool_call


def make_runner(client: FakeClient, registry: ToolRegistry | None = None, **kw):
    """A runner whose children all get `registry` (empty by default)."""
    tools = registry or ToolRegistry()
    return SubagentRunner(
        client=client, model="test-model", build_tools=lambda spawner: tools, **kw
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


# --- depth: may this runner start a subagent? --------------------------------


@pytest.mark.parametrize(
    ("depth", "max_depth", "expected"),
    [(0, 1, True), (1, 1, False), (1, 2, True), (2, 2, False)],
)
def test_can_spawn_while_depth_is_below_max_depth(depth, max_depth, expected):
    runner = make_runner(FakeClient([]), depth=depth, max_depth=max_depth)

    assert runner.can_spawn is expected


def test_default_runner_can_spawn_one_level():
    runner = make_runner(FakeClient([]))

    assert runner.can_spawn is True


def test_run_raises_spawn_not_allowed_at_the_depth_limit():
    client = FakeClient([make_response(content="never")])
    runner = make_runner(client, depth=1, max_depth=1)

    with pytest.raises(SpawnNotAllowed):
        runner.run(SubagentSpec(prompt="go", label="x"))

    assert client.calls == []  # refused before any model call


def test_child_tools_come_from_build_tools_with_a_deeper_spawner():
    tools = ToolRegistry()
    tools.register(FakeTool(name="Fake"))
    spawners = []

    def build_tools(spawner):
        spawners.append(spawner)
        return tools

    client = FakeClient([make_response(content="done")])
    runner = SubagentRunner(
        client=client, model="test-model", build_tools=build_tools, max_depth=3
    )

    runner.run(SubagentSpec(prompt="go", label="x"))

    [child_spawner] = spawners
    assert child_spawner.depth == 1
    assert child_spawner.max_depth == 3
    assert client.calls[0]["tools"] == tools.tools


# --- end to end: main agent -> Skill tool -> subagent -> main agent ----------
#
# Uses the real wiring from main.py and one FakeClient shared by both agents,
# scripted in call order: parent, child, parent.


def test_forked_skill_runs_in_its_own_conversation_end_to_end(tmp_path):
    from app.agent import Agent
    from app.main import build_tool_registry
    from app.skills import SkillRegistry, SkillsLoader

    skill_dir = tmp_path / "apple"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\ndescription: The on-call rotation.\ncontext: fork\n---\n\n"
        "Respond with exactly one word: blueberry\n",
        encoding="utf-8",
    )
    skills = SkillRegistry(SkillsLoader([tmp_path]).load())
    client = FakeClient(
        [
            make_response(
                tool_calls=[make_tool_call("c1", "Skill", {"name": "apple"})]
            ),
            make_response(content="blueberry"),  # the subagent
            make_response(content="The on-call engineer is blueberry."),
        ]
    )
    registry = build_tool_registry(client, "test-model", skills)
    agent = Agent(client=client, registry=registry, model="test-model")
    question = "Who is on the on-call rotation right now?"

    answer = agent.run([question])

    child_messages = client.calls[1]["messages"]
    assert [m["role"] for m in child_messages] == ["user"]
    assert "Respond with exactly one word: blueberry" in child_messages[0]["content"]
    assert question not in child_messages[0]["content"]
    assert {
        "role": "tool",
        "tool_call_id": "c1",
        "content": "Skill apple ran in a separate context and returned: blueberry",
    } in client.calls[2]["messages"]
    assert "blueberry" in answer


def test_subagent_tools_cannot_start_another_subagent(tmp_path):
    # Default max_depth=1: the child's spawner cannot spawn, so a forked skill
    # loads inline there.
    from app.main import build_tool_registry
    from app.skills import SkillRegistry, SkillsLoader

    skill_dir = tmp_path / "apple"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\ndescription: d\ncontext: fork\n---\n\nSay blueberry.\n",
        encoding="utf-8",
    )
    skills = SkillRegistry(SkillsLoader([tmp_path]).load())
    client = FakeClient(
        [
            # inside the subagent, the model calls the same forked skill again
            make_response(
                tool_calls=[make_tool_call("c1", "Skill", {"name": "apple"})]
            ),
            make_response(content="blueberry"),
        ]
    )
    registry = build_tool_registry(client, "test-model", skills)

    result = registry.execute("Skill", name="apple")  # what the main agent does

    # 2 calls: the nested call loaded the body inline instead of a third agent.
    assert len(client.calls) == 2
    nested_result = client.calls[1]["messages"][-1]
    assert nested_result["role"] == "tool"
    assert nested_result["content"].endswith("Say blueberry.")
    assert result.endswith("returned: blueberry")


def test_deeper_max_depth_lets_a_subagent_start_a_grandchild(tmp_path):
    # The same nested script as above, with max_depth=2: the nested call now
    # starts a grandchild, which costs one more model call.
    from app.main import build_tool_registry
    from app.skills import SkillRegistry, SkillsLoader

    skill_dir = tmp_path / "apple"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\ndescription: d\ncontext: fork\n---\n\nSay blueberry.\n",
        encoding="utf-8",
    )
    skills = SkillRegistry(SkillsLoader([tmp_path]).load())
    client = FakeClient(
        [
            # child: calls the forked skill again
            make_response(
                tool_calls=[make_tool_call("c1", "Skill", {"name": "apple"})]
            ),
            make_response(content="blueberry"),  # grandchild answers
            make_response(content="blueberry"),  # child answers
        ]
    )
    registry = build_tool_registry(client, "test-model", skills, max_depth=2)

    result = registry.execute("Skill", name="apple")

    assert len(client.calls) == 3
    grandchild_messages = client.calls[1]["messages"]
    assert [m["role"] for m in grandchild_messages] == ["user"]
    assert grandchild_messages[0]["content"].endswith("Say blueberry.")
    assert client.calls[2]["messages"][-1] == {
        "role": "tool",
        "tool_call_id": "c1",
        "content": "Skill apple ran in a separate context and returned: blueberry",
    }
    assert result.endswith("returned: blueberry")


def test_subagent_logs_under_its_label(caplog):
    client = FakeClient([make_response(content="blueberry")])

    with caplog.at_level("INFO", logger="app.agent"):
        make_runner(client).run(SubagentSpec(prompt="go", label="skill:apple"))

    assert caplog.messages
    assert all(m.startswith("[skill:apple] ") for m in caplog.messages)
