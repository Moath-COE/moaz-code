"""Tests for run_prompt: the path from the raw -p prompt to the final answer.

API these tests pin down:

    run_prompt(prompt, gate, agent, skills, spawner) -> str

An explicit /fork-skill is run here, deterministically, before the main agent
starts: its framed answer is appended as a user message. A failure in it is
raised (main prints it and exits 1); it is never handed to the model.
"""

import pytest

from app.agent import Agent
from app.input.gate import Gate
from app.main import build_spawner, build_tool_registry, run_prompt
from app.skills import SkillRegistry, SkillsLoader
from app.tools.registry import ToolRegistry
from tests.fakes import FakeClient, FakeSpawner, make_response
from tests.instructions import expected_instructions


def write_skill(root, name: str, body: str, fork: bool = False) -> None:
    skill_dir = root / name
    skill_dir.mkdir()
    context = "context: fork\n" if fork else ""
    (skill_dir / "SKILL.md").write_text(
        f"---\ndescription: Does things.\n{context}---\n\n{body}\n",
        encoding="utf-8",
    )


@pytest.fixture
def skills(tmp_path) -> SkillRegistry:
    write_skill(tmp_path, "fork", "Checksum of $ARGUMENTS", fork=True)
    write_skill(tmp_path, "apple", "Apple got $ARGUMENTS")
    return SkillRegistry(SkillsLoader([tmp_path]).load())


def wiring(client: FakeClient, skills: SkillRegistry):
    """The real main wiring: depth-0 runner, the main agent's tools, the agent."""
    spawner = build_spawner(client, "test-model", skills)
    agent = Agent(
        client=client,
        registry=build_tool_registry(spawner),
        model="test-model",
        system_prompt="SYS",
    )
    return agent, spawner


def test_explicit_fork_runs_in_a_subagent_before_the_main_agent(tmp_path, skills):
    client = FakeClient(
        [
            make_response(content="blueberry"),  # the subagent
            make_response(content="final"),  # the main agent
        ]
    )
    agent, spawner = wiring(client, skills)

    answer = run_prompt("/fork 4127", Gate(skills), agent, skills, spawner)

    child_messages = client.calls[0]["messages"]
    assert child_messages == [
        {
            "role": "user",
            "content": expected_instructions(tmp_path, "Checksum of 4127", "fork"),
        }
    ]
    # The typed command never reaches the child. (Plain "/fork" would match the
    # skill's folder path in the header, which is expected.)
    assert "/fork 4127" not in child_messages[0]["content"]
    assert {
        "role": "user",
        "content": "Skill fork ran in a separate context and returned: blueberry",
    } in client.calls[1]["messages"]
    assert answer == "final"


def test_skills_before_the_fork_come_first_then_the_framed_answer(tmp_path, skills):
    client = FakeClient([make_response(content="blueberry"), make_response("final")])
    agent, spawner = wiring(client, skills)

    run_prompt("/apple /fork 4127", Gate(skills), agent, skills, spawner)

    user_messages = [
        m["content"] for m in client.calls[1]["messages"] if m["role"] == "user"
    ]
    assert user_messages == [
        expected_instructions(tmp_path, "Apple got 4127", "apple"),
        "Skill fork ran in a separate context and returned: blueberry",
    ]


def test_failing_explicit_fork_raises_and_the_model_is_never_called(skills):
    client = FakeClient([make_response(content="never")])
    agent = Agent(client=client, registry=ToolRegistry(), model="test-model")
    spawner = FakeSpawner(error=ConnectionError("network down"))

    with pytest.raises(RuntimeError, match="network down"):
        run_prompt("/fork 4127", Gate(skills), agent, skills, spawner)

    assert client.calls == []


def test_prompt_without_a_fork_goes_straight_to_the_main_agent(skills):
    client = FakeClient([make_response(content="hi")])
    agent, spawner = wiring(client, skills)

    answer = run_prompt("hello", Gate(skills), agent, skills, spawner)

    assert client.calls[0]["messages"] == [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "hello"},
    ]
    assert answer == "hi"
