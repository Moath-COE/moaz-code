from app.skills.registry import SkillRegistry

from .base import Tool


class SkillTool(Tool):
    """A tool that loads a skill's instructions into the conversation."""

    def __init__(self, skills_registry: SkillRegistry):
        super().__init__(
            name="Skill",
            description="Load a skill's instructions into the conversation",
            properties={
                "name": {
                    "type": "string",
                    "description": "The name of the skill to use",
                },
                "args": {
                    "type": "string",
                    "description": "Optional arguments for the skill",
                },
            },
            required=["name"],
        )
        self.skills_registry = skills_registry

    def run(self, name: str, args: str = "") -> str:  # pyright: ignore[reportIncompatibleMethodOverride]
        if name not in self.skills_registry:
            return self._unknown_skill_error(name)
        try:
            return self.skills_registry.expand(name=name, arguments=args)
        except RuntimeError as e:
            return f"Error executing skill {name}: {e}"

    def _unknown_skill_error(self, name: str) -> str:
        """Tell the model which names are valid so it can retry."""
        names = self.skills_registry.names
        if not names:
            return f"Error: unknown skill '{name}'. No skills are available."
        return f"Error: unknown skill '{name}'. Available skills: {', '.join(names)}"
