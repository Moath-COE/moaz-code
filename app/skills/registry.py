from app.skills.arguments import substitute_arguments
from app.skills.models import Skill
from app.skills.utils.load_skill_body import load_skill_body


class SkillRegistry:
    """Lookup and advertisement for already-discovered skills."""

    def __init__(self, skills: list[Skill]):
        self._skills = {skill.name: skill for skill in skills}

    def __contains__(self, name: str) -> bool:
        return name in self._skills

    def render(self) -> str:
        """Build the system-prompt text that advertises skills (level 1 only)."""
        if not self._skills:
            return ""

        lines = [
            f"- {skill.name}: {skill.description}"
            for _, skill in sorted(self._skills.items())
        ]
        return "You have access to the following skills:\n\n" + "\n".join(lines)

    def expand(self, name: str, arguments: str = "") -> str:
        """Return the skill's instructions with arguments substituted"""
        instructions = self._get_instructions(name)
        if instructions is None:
            raise ValueError(f"unknown skill name: {name}")
        return substitute_arguments(instructions, arguments)

    def _get_instructions(self, name: str) -> str | None:
        """Header naming the skill's folder, then the body; None for an unknown name."""
        skill = self._skills.get(name)
        if skill is None:
            return None
        body = load_skill_body(skill)
        return f"Skill: {skill.name} (located at {skill.directory})\nPaths in the instructions below are relative to that folder.\n\n{body}"
