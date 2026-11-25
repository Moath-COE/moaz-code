"""Subagents: a second run of the agent loop in a conversation of its own.

A subagent run is one blocking call: spec in, answer out. It shares no
mutable state with its caller (a new Agent means a new message list), so later
it can be moved to a thread without changing what it does.
"""

import logging
from dataclasses import dataclass
from typing import Protocol

from app.agent import Agent
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SubagentSpec:
    """What one subagent run should do. Frozen, so it is safe to hand to a thread."""

    prompt: str  # the only user message the subagent sees
    label: str  # who it is in logs, e.g. "skill:apple"
    system_prompt: str | None = None


class Spawner(Protocol):
    """What tools depend on to start a subagent. Not the Agent class itself."""

    def run(self, spec: SubagentSpec) -> str: ...


class SubagentRunner:
    """Builds a fresh Agent for each spec and runs it to its final answer.

    It raises on failure: turning an error into text for the model is the
    calling tool's job.
    """

    def __init__(
        self,
        client,
        model: str,
        registry: ToolRegistry,
        max_iterations: int = 30,
    ):
        self.client = client
        self.model = model
        self.registry = registry
        self.max_iterations = max_iterations

    def run(self, spec: SubagentSpec) -> str:
        logger.info("subagent %s: starting", spec.label)
        agent = Agent(
            client=self.client,
            registry=self.registry,
            model=self.model,
            max_iterations=self.max_iterations,
            system_prompt=spec.system_prompt,
        )
        answer = agent.run([spec.prompt])
        logger.info("subagent %s: finished", spec.label)
        return answer
