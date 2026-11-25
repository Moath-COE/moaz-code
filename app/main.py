import argparse
import logging
import os
import sys
from pathlib import Path

from app.agent import Agent, Spawner, SubagentRunner
from app.input.gate import Gate
from app.prompts.system_prompt import build_system_prompt
from app.skills import SkillRegistry, SkillsLoader
from app.skills.fork import frame_fork_result, run_forked_skill
from app.tools.bash import BashTool
from app.tools.read import ReadTool
from app.tools.registry import ToolRegistry
from app.tools.skill import SkillTool
from app.tools.write import WriteTool
from app.utils.build_client import build_client

MODEL = "nvidia/nemotron-3.5-super-vl:free"
# MODEL = "anthropic/claude-haiku-4.5"
# MODEL = "qwen/qwen3-vl-8b"


def build_spawner(
    client, model: str, skills_registry: SkillRegistry, max_depth: int = 1
) -> SubagentRunner:
    """The main agent's spawner: the depth-0 runner.

    Its build_tools is the one place that lists the tools. Every agent, main or
    sub, gets its tools from it: the only difference between them is the
    spawner they hold. SubagentRunner hands each child a runner one level
    deeper, and decides whether that one may spawn again.
    """

    def build_tools(spawner: Spawner) -> ToolRegistry:
        registry = ToolRegistry()
        for tool in (
            ReadTool(),
            WriteTool(),
            BashTool(),
            SkillTool(skills_registry, spawner),
        ):
            registry.register(tool)
        return registry

    return SubagentRunner(
        client=client, model=model, build_tools=build_tools, max_depth=max_depth
    )


def build_tool_registry(spawner: SubagentRunner) -> ToolRegistry:
    """The tools for the agent that holds `spawner` (the main agent: depth 0)."""
    return spawner.build_tools(spawner)


def run_prompt(
    prompt: str,
    gate: Gate,
    agent: Agent,
    skills: SkillRegistry,
    spawner: Spawner,
) -> str:
    """Turn the raw prompt into the main agent's final answer.

    An explicit /fork-skill runs here, before the main agent starts, so it does
    not depend on the model choosing to call the Skill tool. Its failure is
    raised as a RuntimeError, never handed to the model.
    """
    parsed = gate.parse_user_prompt(prompt)
    messages = list(parsed.messages)
    if parsed.forked is not None:
        name, args = parsed.forked.name, parsed.forked.rest
        try:
            answer = run_forked_skill(skills, spawner, name, args)
        except Exception as e:
            raise RuntimeError(f"skill {name} failed in its subagent: {e}") from e
        messages.append(frame_fork_result(name, answer))
    return agent.run(messages)


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

    spawner = build_spawner(client, MODEL, skills_registry)
    tool_registry = build_tool_registry(spawner)

    gate = Gate(skills_registry)

    agent = Agent(
        client=client,
        registry=tool_registry,
        model=MODEL,
        system_prompt=SYSTEM_PROMPT,
    )

    try:
        answer = run_prompt(args.p, gate, agent, skills_registry, spawner)
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
