from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    path: Path
    fork: bool = False

    @property
    def directory(self) -> Path:
        """Return the folder that holds SKILL.md."""
        return self.path.parent
