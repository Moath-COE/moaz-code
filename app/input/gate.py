import logging

from app.skills import SkillRegistry

logger = logging.getLogger(__name__)


class Gate:
    """Turns a raw user prompt into what the model sees. Parsing only: it asks
    the registry for skill bodies and never touches the filesystem itself."""

    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    def parse_user_prompt(self, user_prompt: str) -> str:
        """
        Replace a leading /skill with that skill’s body, or return the prompt unchanged.
        """
        words = user_prompt.lstrip().split()
        if not words:
            return user_prompt

        name = self._parse_command_name(words[0])
        body = self.registry.get_body(name) if name else None

        if body is None:
            return user_prompt  # Not a command or unknown skill, return unchanged

        logger.info("Detected skill command: %s", name)

        return body

    def _parse_command_name(self, first_word: str) -> str | None:
        """Return the name in a leading "/name", or None if it isn't a command."""
        if not first_word.startswith("/"):
            return None

        return first_word[1:]  # Remove the leading "/"
