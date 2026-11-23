import json
import logging

logger = logging.getLogger(__name__)


def _preview(text: str, limit: int = 200) -> str:
    """One short line for logs: long values are cut, newlines flattened."""
    text = text.replace("\n", " ")
    return text if len(text) <= limit else text[:limit] + f"... [{len(text)} chars]"


class Agent:
    def __init__(
        self,
        client,
        registry,
        model: str,
        max_iterations: int = 30,
        system_prompt: str | None = None,
    ):
        self.client = client
        self.registry = registry
        self.model = model
        self.system_prompt = system_prompt
        self.messages = (  # add the system prompt as the first message if provided
            [{"role": "system", "content": self.system_prompt}]
            if self.system_prompt
            else []
        )
        self.max_iterations = max_iterations

    def run(self, user_messages: list[str]) -> str:
        for prompt in user_messages:
            message = {"role": "user", "content": prompt}
            self.messages.append(message)
            logger.info("user message added: %s", _preview(prompt))

        while True:
            for i in range(self.max_iterations):
                logger.info("iteration %d: calling %s", i + 1, self.model)
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
                        logger.info(
                            "tool call: %s %s",
                            call.function.name,
                            _preview(call.function.arguments),
                        )
                        try:
                            args = json.loads(call.function.arguments)
                        except json.JSONDecodeError:
                            tool_response = f"JSONDecodeError: Malformed JSON arguments for tool '{call.function.name}'"
                        else:
                            tool_response = self.registry.execute(
                                call.function.name, **args
                            )
                        logger.debug("tool result: %s", _preview(tool_response))
                        self.messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": call.id,
                                "content": tool_response,
                            }
                        )
                elif response.choices[0].message.content:
                    logger.info("final answer after %d iteration(s)", i + 1)
                    return response.choices[0].message.content

            logger.warning("max iterations (%d) reached", self.max_iterations)
            raise RuntimeError("max iterations reached")
