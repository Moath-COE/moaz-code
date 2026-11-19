import logging

from app.skills import Skill
from app.skills.render import load_skill_body

logger = logging.getLogger(__name__)


class Gate:
    def __init__(self, skills: list[Skill]):
        self.skills = {skill.name: skill for skill in skills}

    def parse_user_prompt(self, user_prompt: str) -> str:
        """
        Parse the user prompt and return a structured representation.
        For now, we just return the prompt as is.
        """
        if not user_prompt:
            return ""

        skill_name = self._detect_skill_command(user_prompt.lstrip().split(" ")[0])

        if not skill_name:
            return user_prompt  # Not a command, return unchanged

        skill = self.skills.get(skill_name)
        if skill is None:
            return user_prompt  # Unknown skill, return unchanged

        logger.info("Detected skill command: %s", skill_name)

        return load_skill_body(skill)

    def _detect_skill_command(self, first_word: str) -> str | None:
        """
        Detect if the prompt starts with a skill command (e.g., "/skill_name").
        If so, return the skill name; otherwise, return None.
        """
        if not first_word.startswith("/"):
            return None  # Split and ignore the leading empty part

        skill_name = first_word.split("/")[1]  # Remove the leading "/"

        if skill_name and skill_name in self.skills:
            return skill_name
        else:
            return None
