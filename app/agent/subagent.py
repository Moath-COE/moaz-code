"""Subagents: a second run of the agent loop in a conversation of its own.

A subagent run is one blocking call: spec in, answer out. It shares no
mutable state with its caller (a new Agent means a new message list), so later
it can be moved to a thread without changing what it does.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from app.tools.registry import ToolRegistry

from .core import Agent


@dataclass(frozen=True)
class SubagentSpec:
    """What one subagent run should do. Frozen, so it is safe to hand to a thread."""

    prompt: str  # the only user message the subagent sees
    label: str  # who it is in logs, e.g. "skill:apple"
    system_prompt: str | None = None


class SpawnNotAllowed(RuntimeError):
    """Raised by run() when the runner is already at its depth limit."""


class Spawner(Protocol):
    """What tools depend on to start a subagent. Not the Agent class itself."""

    @property
    def can_spawn(self) -> bool: ...

    def run(self, spec: SubagentSpec) -> str: ...


class SubagentRunner:
    """Builds a fresh Agent for each spec and runs it to its final answer.

    It owns the depth rule: a runner at `depth` may start a subagent only while
    depth < max_depth. Each child gets its tools from `build_tools`, called with
    a runner one level deeper, so the rule follows the agents down the tree.

    It raises on failure: turning an error into text for the model is the
    calling tool's job.
    """

    def __init__(
        self,
        client,
        model: str,
        build_tools: Callable[[Spawner], ToolRegistry],
        max_iterations: int = 30,
        max_depth: int = 1,
        depth: int = 0,
    ):
        self.client = client
        self.model = model
        self.build_tools = build_tools
        self.max_iterations = max_iterations
        self.max_depth = max_depth
        self.depth = depth

    @property
    def can_spawn(self) -> bool:
        return self.depth < self.max_depth

    def run(self, spec: SubagentSpec) -> str:
        if not self.can_spawn:
            raise SpawnNotAllowed(
                f"cannot start subagent {spec.label}: depth {self.depth} "
                f"reached max_depth {self.max_depth}"
            )
        agent = Agent(
            client=self.client,
            registry=self.build_tools(self._child()),
            model=self.model,
            max_iterations=self.max_iterations,
            system_prompt=spec.system_prompt,
            name=spec.label,
        )
        return agent.run([spec.prompt])

    def _child(self) -> SubagentRunner:
        """The runner the child's tools get: same settings, one level deeper."""
        return SubagentRunner(
            client=self.client,
            model=self.model,
            build_tools=self.build_tools,
            max_iterations=self.max_iterations,
            max_depth=self.max_depth,
            depth=self.depth + 1,
        )
