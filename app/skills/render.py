from .models import Skill


def render_skills(skills: list[Skill]) -> str:
    """Build the system-prompt text that advertises skills (level 1 only)."""
    if not skills:
        return ""

    lines = [f"- {skill.name}: {skill.description}" for skill in skills]
    return "You have access to the following skills:\n\n" + "\n".join(lines)
