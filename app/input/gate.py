import logging

from app.skills import Skill
from app.skills.render import load_skill_body

logger = logging.getLogger(__name__)


class Gate:
    def __init__(self, skills: list[Skill]):
        self.skills = {skill.name: skill for skill in skills}

    def parse_user_prompt(self, user_prompt: str) -> str:
        """
        Replace a leading /skill with that skill’s body, or return the prompt unchanged.
        """
        words = user_prompt.lstrip().split()
        if not words:
            return user_prompt

        skill = self._detect_skill_command(words[0])

        if not skill:
            return user_prompt  # Not a command, return unchanged

        logger.info("Detected skill command: %s", skill.name)

        return load_skill_body(skill)

    def _detect_skill_command(self, first_word: str) -> Skill | None:
        """
        Detect if the prompt starts with a skill command (e.g., "/skill_name").
        If so, return the skill; otherwise, return None.
        """
        if not first_word.startswith("/"):
            return None

        skill_name = first_word[1:]  # Remove the leading "/"

        return self.skills.get(skill_name)  # Return the skill if it exists, else None
