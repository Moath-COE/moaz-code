import argparse
import os
import sys

from openai import OpenAI

from app.agent import Agent
from app.tools.bash import BashTool
from app.tools.read import ReadTool
from app.tools.registry import ToolRegistry
from app.tools.write import WriteTool


def build_client():
    API_KEY = os.getenv("OPENROUTER_API_KEY")
    BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")
    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    return client


def main():
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

    agent = Agent(
        client=client,
        registry=tool_registry,
        model="anthropic/claude-haiku-4.5",
        # model="nvidia/nemotron-3-ultra-550b-a55b:free",
    )

    try:
        answer = agent.run(args.p)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    sys.stdout.write(answer)

    print()


if __name__ == "__main__":
    main()
