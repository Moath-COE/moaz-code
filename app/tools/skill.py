import logging

from app.agent import Spawner
from app.skills.fork import frame_fork_result, run_forked_skill
from app.skills.registry import SkillRegistry

from .base import Tool

logger = logging.getLogger(__name__)


class SkillTool(Tool):
    """A tool that loads a skill's instructions into the conversation.

    A thin adapter: a skill with `context: fork` goes to the fork service
    (app.skills.fork) while the spawner can spawn, and any failure becomes text
    for the model. Otherwise the skill's instructions load inline.
    """

    def __init__(self, skills_registry: SkillRegistry, spawner: Spawner):
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
        if skill.fork and self.spawner.can_spawn:
            return self._run_forked(name, args)
        try:
            return self.skills_registry.expand(name=name, arguments=args)
        except RuntimeError as e:
            return f"Error executing skill {name}: {e}"

    def _run_forked(self, name: str, args: str) -> str:
        try:
            answer = run_forked_skill(self.skills_registry, self.spawner, name, args)
        except Exception as e:
            # Isolation boundary: a failing subagent must not crash the main
            # agent. Logged in full, and the model sees the failure as text.
            logger.exception("subagent for skill %s failed", name)
            return f"Error: skill {name} failed in its subagent: {e}"
        return frame_fork_result(name, answer)

    def _unknown_skill_error(self, name: str) -> str:
        """Tell the model which names are valid so it can retry."""
        names = self.skills_registry.names
        if not names:
            return f"Error: unknown skill '{name}'. No skills are available."
        return f"Error: unknown skill '{name}'. Available skills: {', '.join(names)}"
