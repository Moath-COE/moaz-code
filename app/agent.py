import json
import logging

logger = logging.getLogger(__name__)


def _preview(text: str, limit: int = 200) -> str:
    """One short line for logs: long values are cut, newlines flattened."""
    text = text.replace("\n", " ")
    return text if len(text) <= limit else text[:limit] + f"... [{len(text)} chars]"


class _NamedLogger(logging.LoggerAdapter):
    """Prefixes every line with the agent's name, e.g. "[skill:apple] ..."."""

    def process(self, msg, kwargs):
        return f"[{self.extra['name']}] {msg}", kwargs  # pyright: ignore[reportOptionalSubscript]


class Agent:
    """One conversation with the model, and the loop that drives it.

    The messages live on the instance, so a new Agent is a new, empty
    conversation. A subagent is simply another Agent.
    """

    def __init__(
        self,
        client,
        registry,
        model: str,
        max_iterations: int = 30,
        system_prompt: str | None = None,
        name: str = "main",
    ):
        self.client = client
        self.registry = registry
        self.model = model
        self.name = name
        self.system_prompt = system_prompt
        self.messages = (  # add the system prompt as the first message if provided
            [{"role": "system", "content": self.system_prompt}]
            if self.system_prompt
            else []
        )
        self.max_iterations = max_iterations
        self._log = _NamedLogger(logger, {"name": name})

    def run(self, user_messages: list[str]) -> str:
        for prompt in user_messages:
            message = {"role": "user", "content": prompt}
            self.messages.append(message)
            self._log.info("user message added: %s", _preview(prompt))

        for i in range(self.max_iterations):
            self._log.info("iteration %d: calling %s", i + 1, self.model)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=self.registry.tools,
            )

            if not response.choices:
                raise RuntimeError("no choices in response")

            message = response.choices[0].message
            self.messages.append(message)

            if message.tool_calls:
                for call in message.tool_calls:
                    self.messages.append(self._execute_tool_call(call))
            elif message.content:
                self._log.info("final answer after %d iteration(s)", i + 1)
                return message.content

        self._log.warning("max iterations (%d) reached", self.max_iterations)
        raise RuntimeError("max iterations reached")

    def _execute_tool_call(self, call) -> dict:
        """Run one tool call and return the tool message for the conversation."""
        name, raw_args = call.function.name, call.function.arguments
        self._log.info("tool call: %s %s", name, _preview(raw_args))
        try:
            args = json.loads(raw_args)
        except json.JSONDecodeError:
            result = f"JSONDecodeError: Malformed JSON arguments for tool '{name}'"
        else:
            result = self.registry.execute(name, **args)
        self._log.debug("tool result: %s", _preview(result))
        return {"role": "tool", "tool_call_id": call.id, "content": result}
