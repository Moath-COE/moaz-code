import sys
from pathlib import Path

import yaml

from app.skills.models import Skill


class SkillLoader:
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

    # inside SkillLoader

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

        data = _parse_frontmatter(text)
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


def _parse_frontmatter(text: str) -> dict | None:
    """Return the YAML mapping between the first two '---' lines, or None."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    for end, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":  # first closing marker only
            raw = "\n".join(lines[1:end])
            break
    else:  # no closing marker
        return None

    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        return None
    return data if isinstance(data, dict) else None
