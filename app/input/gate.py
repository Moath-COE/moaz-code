import logging
from dataclasses import dataclass, field

from app.input.command import Command, parse_command
from app.skills import SkillRegistry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParsedPrompt:
    """What the user prompt turned into.

    messages: the user messages for the main conversation.
    forked:   a `context: fork` skill the user typed, for the caller to run in
              a subagent. Gate only reports it; it never runs anything.
    """

    messages: list[str] = field(default_factory=list)
    forked: Command | None = None


class Gate:
    """Turns a raw user prompt into what the model sees. Parsing only: it asks
    the skills registry for skill instructions and never touches the filesystem itself."""

    def __init__(self, skills_registry: SkillRegistry):
        self.skills_registry = skills_registry

    def parse_user_prompt(self, user_prompt: str) -> ParsedPrompt:
        """
        Replace a stacked skill calls with these skills' body, or return the prompt unchanged.

        A forked skill ends the run as its last item: it is reported in
        `forked` with the text after it as its arguments, and never expanded
        here. Normal skills before it share that same argument text.
        """
        names, rest, forked = [], user_prompt, None

        while command := parse_command(rest):
            skill = self.skills_registry.get(command.name)
            if skill is None:
                break
            logger.info("Detected skill command: %s", command.name)
            rest = command.rest
            if skill.fork:
                forked = command
                break
            names.append(command.name)

        if not names and forked is None:
            return ParsedPrompt(messages=[user_prompt])
        messages = [self.skills_registry.expand(name, rest) for name in names]
        return ParsedPrompt(messages=messages, forked=forked)
