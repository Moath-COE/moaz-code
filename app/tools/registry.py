from .base import Tool


class ToolRegistry:
    """Registry for managing and executing tools."""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool):
        if tool.name in self._tools:
            raise ValueError(f"Tool with name '{tool.name}' is already registered.")

        self._tools[tool.name] = tool

    @property
    def tools(self) -> list[dict]:
        return [tool.schema() for tool in self._tools.values()]

    def execute(self, tool_name: str, **kwargs) -> str:
        tool = self._tools.get(tool_name)
        if not tool:
            return f"Tool '{tool_name}' is not registered."
        return tool.run(**kwargs)
