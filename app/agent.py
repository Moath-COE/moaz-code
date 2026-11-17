import json


class Agent:
    def __init__(self, client, registry, model: str, max_iterations: int = 10):
        self.client = client
        self.registry = registry
        self.model = model
        self.messages = []
        self.max_iterations = max_iterations

    def run(self, prompt: str) -> str:
        self.messages.append({"role": "user", "content": prompt})

        while True:
            for _ in range(self.max_iterations):
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=self.registry.tools,
                )

                if not response.choices or len(response.choices) == 0:
                    raise RuntimeError("no choices in response")

                self.messages.append(response.choices[0].message)

                if response.choices[0].message.tool_calls:
                    for call in response.choices[0].message.tool_calls:
                        try:
                            args = json.loads(call.function.arguments)
                        except json.JSONDecodeError:
                            tool_response = f"JSONDecodeError: Malformed JSON arguments for tool '{call.function.name}'"
                        else:
                            tool_response = self.registry.execute(
                                call.function.name, **args
                            )
                        self.messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": call.id,
                                "content": tool_response,
                            }
                        )
                elif response.choices[0].message.content:
                    return response.choices[0].message.content

            raise RuntimeError("max iterations reached")
