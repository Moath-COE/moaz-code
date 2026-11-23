import logging
import re

from app.skills import SkillRegistry
from app.skills.arguments import substitute_arguments

logger = logging.getLogger(__name__)

# optional leading whitespace, "/", the name, any whitespace, then everything else
_COMMAND = re.compile(r"\s*/(\S+)\s*(.*)", re.DOTALL)


class Gate:
    """Turns a raw user prompt into what the model sees. Parsing only: it asks
    the registry for skill instructions and never touches the filesystem itself."""

    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    def parse_user_prompt(self, user_prompt: str) -> list[str]:
        """
        Replace a leading /skill with that skill’s body, or return the prompt unchanged.
        """
        command_instructions, command_arguments = self._detect_skill_commands(
            user_prompt
        )
        if not command_instructions:
            return [user_prompt]  # Not a command or unknown skill, return unchanged

        # If we have commands, we substitute their arguments and return the expanded instructions. Each command gets the same remaining text.
        result = []
        for cmd_instruction in command_instructions:
            result.append(substitute_arguments(cmd_instruction, command_arguments))

        return result

    def _detect_skill_commands(self, user_prompt: str) -> tuple[list[str], str]:
        """Return detected skill instructions and arguments, None if there are none."""
        instructions = []
        arguments = user_prompt
        while match := _COMMAND.match(arguments):
            name, after = match.groups()
            body = self.registry.get_instructions(name)
            if body is None:  # unknown skill: expansion stops here
                break
            instructions.append(body)
            logger.info("Detected skill command: %s", name)
            arguments = after

        return instructions, arguments
