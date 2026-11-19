import sys
from pathlib import Path

from app.skills.models import Skill
from app.skills.parse_yaml import parse_frontmatter


class SkillsLoader:
    """Load skills from one or more root directories. Each root is a folder that contains zero or more skill subfolders. Each skill subfolder must contain a SKILL.md file with YAML frontmatter that defines the skill's description."""

    def __init__(self, roots: list[Path]):
        self.roots = roots

    def load(self) -> list[Skill]:
        skills: dict[str, Skill] = {}  # name -> Skill

        for root in self.roots:  # roots are in priority order
            if not root.is_dir():  # missing root is normal
                continue
            for skill_dir in sorted(root.iterdir()):
                if not skill_dir.is_dir():  # ignore plain files
                    continue
                if skill_dir.name in skills:  # an earlier root already won
                    continue
                skill = self._load_one(skill_dir)
                if skill is not None:  # None means "skipped"
                    skills[skill.name] = skill

        return sorted(skills.values(), key=lambda s: s.name)

    # inside SkillsLoader

    def _skip(self, skill_dir: Path, reason: str) -> None:
        print(f"skipping skill '{skill_dir.name}': {reason}", file=sys.stderr)

    def _load_one(self, skill_dir: Path) -> Skill | None:
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            self._skip(skill_dir, "no SKILL.md")
            return None

        try:
            text = skill_file.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as e:
            self._skip(skill_dir, f"cannot read SKILL.md ({e})")
            return None

        data = parse_frontmatter(text)
        if data is None:
            self._skip(skill_dir, "missing or invalid frontmatter")
            return None

        description = data.get("description")
        if not isinstance(description, str) or not description.strip():
            self._skip(skill_dir, "missing description")
            return None

        return Skill(
            name=skill_dir.name,
            description=" ".join(description.split()),
            path=skill_file,
        )
