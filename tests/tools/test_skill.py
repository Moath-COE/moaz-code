"""Tests for SkillTool: the tool the model calls to load a skill by name.

API these tests pin down:

    SkillTool(registry: SkillRegistry)
    .name == "Skill"
    .schema()                  -> required ["name"], optional "args"
    .run(name, args="") -> str -> the expanded instructions, or an "Error..." string

SkillTool only delegates to SkillRegistry.expand. It never reads files itself,
and it never raises: the model must see the failure as text and recover.
"""

import pytest

from app.skills import SkillRegistry, SkillsLoader
from app.tools.registry import ToolRegistry
from app.tools.skill import SkillTool
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
    return SkillTool(SkillRegistry(SkillsLoader([tmp_path]).load()))


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
    result = SkillTool(SkillRegistry([])).run(name="apple")

    assert "apple" in result
    assert "No skills are available" in result
    assert "Available skills" not in result


def test_unknown_skill_error_does_not_leak_other_bodies(tmp_path):
    tool = tool_with(tmp_path, apple="SECRET BODY TEXT")

    assert "SECRET BODY TEXT" not in tool.run(name="mango")


def test_skill_with_no_skills_at_all_returns_an_error_string():
    tool = SkillTool(SkillRegistry([]))

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
