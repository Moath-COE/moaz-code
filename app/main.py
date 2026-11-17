import argparse
import json
import os
import sys

from openai import OpenAI
from tools.read import ReadTool
from tools.registry import ToolRegistry

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")

read_tool = ReadTool()
tool_registry = ToolRegistry()
tool_registry.register(read_tool)


def call_openai(client, messages):
    return client.chat.completions.create(
        # model="nvidia/nemotron-3-ultra-550b-a55b:free",
        model="anthropic/claude-haiku-4.5",
        messages=messages,
        # Define the tools that the model can call
        tools=[tool_registry.tools],
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("-p", required=True)
    args = p.parse_args()

    if not API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    messages: list = [{"role": "user", "content": args.p}]

    while True:
        response = call_openai(client, messages)

        if not response.choices or len(response.choices) == 0:
            raise RuntimeError("no choices in response")

        messages.append(response.choices[0].message)

        if response.choices[0].message.tool_calls:
            for call in response.choices[0].message.tool_calls:
                tool_response = tool_registry.execute(
                    call.function.name, **json.loads(call.function.arguments)
                )
                messages.append(
                    {"role": "tool", "tool_call_id": call.id, "content": tool_response}
                )
        elif response.choices[0].message.content:
            sys.stdout.write(response.choices[0].message.content)
            break


if __name__ == "__main__":
    main()
