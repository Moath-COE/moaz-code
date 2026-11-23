import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    name: str
    rest: str


_COMMAND = re.compile(r"\s*/(\S+)\s*(.*)", re.DOTALL)


def parse_command(text: str) -> Command | None:
    match = _COMMAND.match(text)

    if match is None:
        return None
    name, rest = match.groups()
    return Command(name=name, rest=rest)
