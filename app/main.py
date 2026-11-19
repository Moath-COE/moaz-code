import argparse
import logging
import os
import sys
from pathlib import Path

from app.agent import Agent
from app.input.gate import Gate
from app.prompts.system_prompt import build_system_prompt
from app.skills import SkillsLoader, render_skills
from app.tools.bash import BashTool
from app.tools.read import ReadTool
from app.tools.registry import ToolRegistry
from app.tools.write import WriteTool
from app.utils.build_client import build_client


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

    tool_registry = ToolRegistry()

    read_tool = ReadTool()
    write_tool = WriteTool()
    bash_tool = BashTool()

    tool_registry.register(read_tool)
    tool_registry.register(write_tool)
    tool_registry.register(bash_tool)

    SKILL_ROOTS = [Path(".agents/skills"), Path(".claude/skills")]

    skills = SkillsLoader(SKILL_ROOTS).load()
    skills_prompt = render_skills(skills)

    SYSTEM_PROMPT = build_system_prompt(skills_prompt)

    gate = Gate(skills)

    agent = Agent(
        client=client,
        registry=tool_registry,
        # model="anthropic/claude-haiku-4.5",
        model="nvidia/nemotron-3.5-super-vl:free",
        system_prompt=SYSTEM_PROMPT,
    )

    try:
        user_prompt = gate.parse_user_prompt(args.p)
        answer = agent.run(user_prompt)
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
