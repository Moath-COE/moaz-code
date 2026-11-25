import logging

from app.agent import Spawner, SubagentSpec
from app.skills.registry import SkillRegistry

from .base import Tool

logger = logging.getLogger(__name__)


class SkillTool(Tool):
    """A tool that loads a skill's instructions into the conversation.

    A skill with `context: fork` is handed to the spawner instead: it runs in a
    subagent with a conversation of its own, and only its answer comes back.
    Without a spawner (inside a subagent), forked skills load inline.
    """

    def __init__(self, skills_registry: SkillRegistry, spawner: Spawner | None = None):
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
        self.spawner = spawner

    def run(self, name: str, args: str = "") -> str:  # pyright: ignore[reportIncompatibleMethodOverride]
        skill = self.skills_registry.get(name)
        if skill is None:
            return self._unknown_skill_error(name)
        try:
            instructions = self.skills_registry.expand(name=name, arguments=args)
        except RuntimeError as e:
            return f"Error executing skill {name}: {e}"

        if skill.fork and self.spawner is not None:
            return self._run_in_subagent(self.spawner, name, instructions)
        return instructions

    def _run_in_subagent(self, spawner: Spawner, name: str, instructions: str) -> str:
        spec = SubagentSpec(prompt=instructions, label=f"skill:{name}")
        try:
            answer = spawner.run(spec)
        except Exception as e:
            # Isolation boundary: a failing subagent must not crash the main
            # agent. Logged in full, and the model sees the failure as text.
            logger.exception("subagent for skill %s failed", name)
            return f"Error: skill {name} failed in its subagent: {e}"
        return f"Skill {name} ran in a separate context and returned: {answer}"

    def _unknown_skill_error(self, name: str) -> str:
        """Tell the model which names are valid so it can retry."""
        names = self.skills_registry.names
        if not names:
            return f"Error: unknown skill '{name}'. No skills are available."
        return f"Error: unknown skill '{name}'. Available skills: {', '.join(names)}"
