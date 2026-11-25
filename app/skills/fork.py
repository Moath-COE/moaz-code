"""Run a `context: fork` skill in a subagent.

One service for both ways a forked skill starts: the model calling the Skill
tool, and the user typing /skill. It depends only on the Spawner Protocol, so
it never knows how (or where) the subagent actually runs.
"""

from app.agent import Spawner, SubagentSpec
from app.skills.registry import SkillRegistry


def run_forked_skill(
    skills: SkillRegistry, spawner: Spawner, name: str, args: str = ""
) -> str:
    """Expand the skill and run it in a subagent; return the subagent's raw answer.

    Raises on any failure. Turning it into text (or an exit) is the caller's job.
    """
    instructions = skills.expand(name, args)
    return spawner.run(SubagentSpec(prompt=instructions, label=f"skill:{name}"))


def frame_fork_result(name: str, answer: str) -> str:
    """The text the main conversation sees in place of the skill's body."""
    return f"Skill {name} ran in a separate context and returned: {answer}"
