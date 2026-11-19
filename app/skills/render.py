from app.skills.parse_yaml import parse_body

from .models import Skill


def render_skills(skills: list[Skill]) -> str:
    """Build the system-prompt text that advertises skills (level 1 only)."""
    if not skills:
        return ""

    lines = [f"- {skill.name}: {skill.description}" for skill in skills]
    return "You have access to the following skills:\n\n" + "\n".join(lines)


def load_skill_body(skill: Skill) -> str:
    """Load the body of a skill's SKILL.md file."""
    if skill is None:
        return "[Skill not found]"
    skill_file = skill.path
    try:
        return parse_body(skill_file.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError) as e:
        raise RuntimeError(f"cannot read SKILL.md for skill '{skill.name}': {e}") from e
