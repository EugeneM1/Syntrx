"""Shared agent base class — gives every stage a consistent logging shape."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

logger = logging.getLogger("syntrx.agent")
I = TypeVar("I")
O = TypeVar("O")


@dataclass
class AgentStep:
    name: str
    duration_ms: int
    summary: str
    metadata: dict[str, Any]


class Agent(ABC, Generic[I, O]):
    name: str = "agent"

    @abstractmethod
    def run(self, input_data: I) -> O: ...

    def __call__(self, input_data: I) -> tuple[O, AgentStep]:
        start = time.monotonic()
        out = self.run(input_data)
        elapsed = int((time.monotonic() - start) * 1000)
        step = AgentStep(
            name=self.name,
            duration_ms=elapsed,
            summary=self.describe(out),
            metadata=self.metadata(out),
        )
        logger.info("agent=%s ms=%d %s", self.name, elapsed, step.summary)
        return out, step

    def describe(self, output: O) -> str:  # noqa: ARG002
        return f"{self.name} complete"

    def metadata(self, output: O) -> dict[str, Any]:  # noqa: ARG002
        return {}
