import logging

from app.input.command import parse_command
from app.skills import SkillRegistry

logger = logging.getLogger(__name__)


class Gate:
    """Turns a raw user prompt into what the model sees. Parsing only: it asks
    the skills registry for skill instructions and never touches the filesystem itself."""

    def __init__(self, skills_registry: SkillRegistry):
        self.skills_registry = skills_registry

    def parse_user_prompt(self, user_prompt: str) -> list[str]:
        """
        Replace a stacked skill calls with these skills' body, or return the prompt unchanged.

        A forked skill ends the run like a non-skill token: it must run in a
        subagent, so it stays as text for the model to reach via the Skill tool.
        """
        names, rest = [], user_prompt

        while command := parse_command(rest):
            skill = self.skills_registry.get(command.name)
            if skill is None or skill.fork:
                break
            logger.info("Detected skill command: %s", command.name)
            names.append(command.name)
            rest = command.rest

        if not names:
            return [user_prompt]
        return [self.skills_registry.expand(name, rest) for name in names]
