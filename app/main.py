import argparse
import logging
import os
import sys
from pathlib import Path

from app.agent import Agent
from app.input.gate import Gate
from app.prompts.system_prompt import build_system_prompt
from app.skills import SkillRegistry, SkillsLoader
from app.subagent import SubagentRunner
from app.tools.bash import BashTool
from app.tools.read import ReadTool
from app.tools.registry import ToolRegistry
from app.tools.skill import SkillTool
from app.tools.write import WriteTool
from app.utils.build_client import build_client

MODEL = "nvidia/nemotron-3.5-super-vl:free"
# MODEL = "anthropic/claude-haiku-4.5"
# MODEL = "qwen/qwen3-vl-8b"


def build_tool_registry(
    client, model: str, skills_registry: SkillRegistry
) -> ToolRegistry:
    """The main agent's tools, plus the subagent runner that forked skills use.

    Built in two layers so there is no cycle: the subagent's tools first (its
    Skill tool has no spawner, so subagents never start subagents), then the
    runner over them, then the main tools whose Skill tool can fork.
    """
    read_tool, write_tool, bash_tool = ReadTool(), WriteTool(), BashTool()

    subagent_registry = ToolRegistry()
    for tool in (read_tool, write_tool, bash_tool, SkillTool(skills_registry)):
        subagent_registry.register(tool)

    runner = SubagentRunner(client=client, model=model, registry=subagent_registry)

    main_registry = ToolRegistry()
    for tool in (
        read_tool,
        write_tool,
        bash_tool,
        SkillTool(skills_registry, spawner=runner),
    ):
        main_registry.register(tool)
    return main_registry


def main():
    # Logs go to stderr: stdout must hold only the final answer.
    logging.basicConfig(
        level=logging.WARNING, format="%(levelname)-7s %(message)s", stream=sys.stderr
    )
    logging.getLogger("app").setLevel(os.getenv("LOG_LEVEL", "WARNING").upper())

    p = argparse.ArgumentParser()
    p.add_argument("-p", required=True)
    args = p.parse_args()

    client = build_client()

    SKILL_ROOTS = [Path(".agents/skills"), Path(".claude/skills")]

    skills = SkillsLoader(SKILL_ROOTS).load()
    skills_registry = SkillRegistry(skills)

    SYSTEM_PROMPT = build_system_prompt(skills_registry.render())

    tool_registry = build_tool_registry(client, MODEL, skills_registry)

    gate = Gate(skills_registry)

    agent = Agent(
        client=client,
        registry=tool_registry,
        model=MODEL,
        system_prompt=SYSTEM_PROMPT,
    )

    try:
        user_messages = gate.parse_user_prompt(args.p)
        answer = agent.run(user_messages)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    if sys.stdout.isatty():
        # Only on a terminal: a pipe (the CodeCrafters tester) gets the bare answer.
        print("\n" + "─" * 40, file=sys.stdout)
    sys.stdout.write(answer)

    print()


if __name__ == "__main__":
    main()
