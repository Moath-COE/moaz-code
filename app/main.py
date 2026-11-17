import argparse
import os
import sys
import json

from openai import OpenAI

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = os.getenv("OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1")

def execute_tool_call(tool_call):
    if (tool_call.function.name == "Read"):
        arguments = json.loads(tool_call.function.arguments)
        file_content = read_tool(arguments["file_path"])
        return file_content
    else:
        return f"Unknown tool: {tool_call.function.name}"

def read_tool(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def call_openai(client, messages):
    return client.chat.completions.create(
        # model="nvidia/nemotron-3-ultra-550b-a55b:free",
        model="anthropic/claude-haiku-4.5",
        messages=messages,
        # Define the tools that the model can call
        tools=[{
            "type": "function",
            "function": {
                "name": "Read",
                "description": "Read and return the contents of a file",
                "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                    "type": "string",
                    "description": "The path to the file to read"
                    }
                },
                "required": ["file_path"]
                }
            }
            }]
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
                tool_response = execute_tool_call(call)
                messages.append({"role": "tool", "tool_call_id": call.id, "content": tool_response})
        elif (response.choices[0].message.content):
            sys.stdout.write(response.choices[0].message.content)
            break



if __name__ == "__main__":
    main()


