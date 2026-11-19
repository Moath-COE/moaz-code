from app.skills.models import Skill
from app.skills.utils.parse_yaml import parse_body


def load_skill_body(skill: Skill) -> str:
    """Load the body of a skill's SKILL.md file."""
    skill_file = skill.path
    try:
        return parse_body(skill_file.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError) as e:
        raise RuntimeError(f"cannot read SKILL.md for skill '{skill.name}': {e}") from e
