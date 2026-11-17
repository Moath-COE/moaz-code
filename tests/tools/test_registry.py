import pytest

from app.tools.base import Tool
from app.tools.registry import ToolRegistry


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


@pytest.fixture
def registry() -> ToolRegistry:
    return ToolRegistry()


def test_registered_tool_schema_is_exposed(registry):
    tool = FakeTool(name="Fake")
    registry.register(tool)

    schemas = registry.tools

    assert schemas == [tool.schema()]


def test_execute_runs_the_named_tool_and_returns_its_output(registry):
    registry.register(FakeTool(name="Fake", output="hello"))

    result = registry.execute("Fake", x="1")

    assert result == "hello"


def test_execute_forwards_kwargs_to_the_tool(registry):
    tool = FakeTool(name="Fake")
    registry.register(tool)

    registry.execute("Fake", x="1")

    assert tool.calls == [{"x": "1"}]


def test_execute_unknown_tool_returns_error_message(registry):
    result = registry.execute("Nope")

    assert "Nope" in result


def test_empty_registry_exposes_no_schemas(registry):
    assert registry.tools == []


def test_execute_runs_the_right_tool(registry):
    tool1 = FakeTool(name="Tool1", output="output1")
    tool2 = FakeTool(name="Tool2", output="output2")
    registry.register(tool1)
    registry.register(tool2)

    result = registry.execute("Tool1", x="value")

    assert result == "output1"
    assert tool1.calls == [{"x": "value"}]
    assert tool2.calls == []


def test_register_duplicate_name_raises_value_error(registry):
    tool1 = FakeTool(name="Duplicate", output="first")
    tool2 = FakeTool(name="Duplicate", output="second")

    registry.register(tool1)

    with pytest.raises(ValueError, match="Duplicate"):
        registry.register(tool2)

    assert registry.execute("Duplicate") == "first"
