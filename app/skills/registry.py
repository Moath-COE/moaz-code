from app.skills.models import Skill
from app.skills.utils.load_skill_body import load_skill_body


class SkillRegistry:
    """Lookup and advertisement for already-discovered skills."""

    def __init__(self, skills: list[Skill]):
        self._skills = {skill.name: skill for skill in skills}

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def get_body(self, name: str) -> str | None:
        """The skill's body (level 2), read on demand; None for an unknown name."""
        skill = self.get(name)
        return None if skill is None else load_skill_body(skill)

    def render(self) -> str:
        """Build the system-prompt text that advertises skills (level 1 only)."""
        if not self._skills:
            return ""

        lines = [
            f"- {skill.name}: {skill.description}"
            for _, skill in sorted(self._skills.items())
        ]
        return "You have access to the following skills:\n\n" + "\n".join(lines)
