"""Tests for SkillTool: the tool the model calls to load a skill by name.

API these tests pin down:

    SkillTool(registry: SkillRegistry, spawner: Spawner)
    .name == "Skill"
    .schema()                  -> required ["name"], optional "args"
    .run(name, args="") -> str -> the expanded instructions, or an "Error..." string

SkillTool delegates to SkillRegistry.expand, and for a `context: fork` skill
to the spawner (see Phase 6). It never reads files itself,
and it never raises: the model must see the failure as text and recover.
"""

import pytest

from app.skills import SkillRegistry, SkillsLoader
from app.tools.registry import ToolRegistry
from app.tools.skill import SkillTool
from tests.fakes import FakeSpawner
from tests.instructions import expected_instructions


def write_skill(root, name: str, body: str, description: str = "Does things.") -> None:
    skill_dir = root / name
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        f"---\ndescription: {description}\n---\n\n{body}\n", encoding="utf-8"
    )


def tool_with(tmp_path, **bodies: str) -> SkillTool:
    """A SkillTool over real skill files: one skill per keyword, name -> body."""
    for name, body in bodies.items():
        write_skill(tmp_path, name, body)
    return SkillTool(SkillRegistry(SkillsLoader([tmp_path]).load()), FakeSpawner())


# --- Phase 1: the schema is the contract with the model ----------------------


def test_schema_names_the_tool_skill(tmp_path):
    schema = tool_with(tmp_path).schema()

    assert schema["type"] == "function"
    assert schema["function"]["name"] == "Skill"


def test_schema_requires_only_name(tmp_path):
    parameters = tool_with(tmp_path).schema()["function"]["parameters"]

    assert parameters["required"] == ["name"]


def test_schema_declares_name_and_args_as_strings(tmp_path):
    properties = tool_with(tmp_path).schema()["function"]["parameters"]["properties"]

    assert set(properties) == {"name", "args"}
    assert properties["name"]["type"] == "string"
    assert properties["args"]["type"] == "string"


def test_schema_has_a_description_for_the_model(tmp_path):
    function = tool_with(tmp_path).schema()["function"]

    assert function["description"]  # the model reads this to know when to call it


# --- Phase 2: a known skill returns its instructions -------------------------


def test_run_returns_the_skill_instructions(tmp_path):
    tool = tool_with(tmp_path, apple="Say blueberry.")

    assert tool.run(name="apple") == expected_instructions(tmp_path, "Say blueberry.")


def test_run_returns_only_the_requested_skill(tmp_path):
    # The decoy rule of the stage: loading both skills fails the tester.
    tool = tool_with(tmp_path, apple="Say blueberry.", grape="Say raisin.")

    result = tool.run(name="apple")

    assert "blueberry" in result
    assert "raisin" not in result


# --- Phase 3: args fill the placeholders -------------------------------------


def test_run_fills_the_arguments_placeholder(tmp_path):
    tool = tool_with(tmp_path, apple="Checksum of $ARGUMENTS")

    assert tool.run(name="apple", args="data.txt").endswith("Checksum of data.txt")


def test_run_fills_positional_placeholders(tmp_path):
    tool = tool_with(tmp_path, apple="$1 $0")

    assert tool.run(name="apple", args="mango pear").endswith("pear mango")


def test_run_without_args_empties_the_placeholders(tmp_path):
    tool = tool_with(tmp_path, apple="[$ARGUMENTS]")

    assert tool.run(name="apple").endswith("[]")


# --- Phase 4: failures come back as strings, never exceptions ----------------


def test_unknown_skill_returns_an_error_string_naming_it(tmp_path):
    tool = tool_with(tmp_path, apple="Say blueberry.")

    result = tool.run(name="mango")

    assert result.startswith("Error")
    assert "mango" in result


def test_unknown_skill_error_lists_the_available_names(tmp_path):
    tool = tool_with(tmp_path, apple="Say blueberry.", grape="Say raisin.")

    result = tool.run(name="mango")

    assert "Available skills: apple, grape" in result


def test_unknown_skill_error_says_so_when_there_are_no_skills():
    result = SkillTool(SkillRegistry([]), FakeSpawner()).run(name="apple")

    assert "apple" in result
    assert "No skills are available" in result
    assert "Available skills" not in result


def test_unknown_skill_error_does_not_leak_other_bodies(tmp_path):
    tool = tool_with(tmp_path, apple="SECRET BODY TEXT")

    assert "SECRET BODY TEXT" not in tool.run(name="mango")


def test_skill_with_no_skills_at_all_returns_an_error_string():
    tool = SkillTool(SkillRegistry([]), FakeSpawner())

    assert tool.run(name="apple").startswith("Error")


def test_unreadable_skill_file_returns_an_error_string(tmp_path):
    tool = tool_with(tmp_path, apple="Say blueberry.")
    (tmp_path / "apple" / "SKILL.md").unlink()  # discovered, then gone

    result = tool.run(name="apple")

    assert result.startswith("Error")
    assert "apple" in result


# --- Phase 5: it works through the ToolRegistry (what the agent really does) -


@pytest.fixture
def tool_registry(tmp_path) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(tool_with(tmp_path, apple="Say blueberry."))
    return registry


def test_registry_executes_skill_with_only_name(tool_registry):
    # `args` is optional: ToolRegistry must not reject a call without it.
    assert "blueberry" in tool_registry.execute("Skill", name="apple")


def test_registry_executes_skill_with_name_and_args(tmp_path):
    registry = ToolRegistry()
    registry.register(tool_with(tmp_path, apple="Checksum of $ARGUMENTS"))

    assert registry.execute("Skill", name="apple", args="a.txt").endswith(
        "Checksum of a.txt"
    )


def test_registry_advertises_the_skill_schema(tool_registry):
    assert [schema["function"]["name"] for schema in tool_registry.tools] == ["Skill"]


# --- Phase 6: a forked skill runs in a subagent ------------------------------
#
#   SkillTool(registry, spawner: Spawner)
#
# A skill with `context: fork` is not returned to the model. Its expanded
# instructions go to the spawner, and only the subagent's answer comes back.


def write_forked_skill(root, name: str, body: str) -> None:
    skill_dir = root / name
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        f"---\ndescription: Does things.\ncontext: fork\n---\n\n{body}\n",
        encoding="utf-8",
    )


def forked_tool(tmp_path, spawner, body: str = "Say blueberry.") -> SkillTool:
    write_forked_skill(tmp_path, "apple", body)
    write_skill(tmp_path, "grape", "Say raisin.")
    return SkillTool(SkillRegistry(SkillsLoader([tmp_path]).load()), spawner=spawner)


def test_forked_skill_sends_its_instructions_to_the_spawner(tmp_path):
    spawner = FakeSpawner()
    tool = forked_tool(tmp_path, spawner)

    tool.run(name="apple")

    assert [spec.prompt for spec in spawner.specs] == [
        expected_instructions(tmp_path, "Say blueberry.")
    ]


def test_forked_skill_spec_is_labelled_and_has_no_system_prompt(tmp_path):
    spawner = FakeSpawner()
    tool = forked_tool(tmp_path, spawner)

    tool.run(name="apple")

    [spec] = spawner.specs
    assert spec.label == "skill:apple"
    assert spec.system_prompt is None


def test_forked_skill_fills_arguments_before_spawning(tmp_path):
    spawner = FakeSpawner()
    tool = forked_tool(tmp_path, spawner, body="Checksum of $ARGUMENTS")

    tool.run(name="apple", args="data.txt")

    assert spawner.specs[0].prompt.endswith("Checksum of data.txt")


def test_forked_skill_returns_the_subagent_answer_in_the_stage_framing(tmp_path):
    tool = forked_tool(tmp_path, FakeSpawner(answer="blueberry"))

    result = tool.run(name="apple")

    assert result == "Skill apple ran in a separate context and returned: blueberry"


def test_forked_skill_result_does_not_contain_the_body(tmp_path):
    tool = forked_tool(tmp_path, FakeSpawner(answer="x"), body="SECRET BODY TEXT")

    assert "SECRET BODY TEXT" not in tool.run(name="apple")


def test_normal_skill_never_calls_the_spawner(tmp_path):
    spawner = FakeSpawner()
    tool = forked_tool(tmp_path, spawner)

    result = tool.run(name="grape")

    assert spawner.specs == []
    assert result == expected_instructions(tmp_path, "Say raisin.", name="grape")


def test_failing_subagent_returns_an_error_string_naming_the_skill(tmp_path):
    tool = forked_tool(tmp_path, FakeSpawner(error=RuntimeError("max iterations")))

    result = tool.run(name="apple")

    assert result.startswith("Error")
    assert "apple" in result
    assert "max iterations" in result


def test_any_subagent_exception_is_contained(tmp_path):
    # e.g. an API error deep inside the subagent must not crash the main agent.
    tool = forked_tool(tmp_path, FakeSpawner(error=ConnectionError("network down")))

    assert tool.run(name="apple").startswith("Error")


def test_forked_skill_loads_inline_when_the_spawner_cannot_spawn(tmp_path):
    # At the depth limit (e.g. inside a subagent), a forked skill loads inline.
    spawner = FakeSpawner(can_spawn=False)
    tool = forked_tool(tmp_path, spawner)

    result = tool.run(name="apple")

    assert spawner.specs == []
    assert result == expected_instructions(tmp_path, "Say blueberry.")
