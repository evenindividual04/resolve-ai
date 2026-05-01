from __future__ import annotations

from abc import ABC, abstractmethod

from domain.models import Event
from workflow.orchestrator import Orchestrator


class OrchestrationAdapter(ABC):
    @abstractmethod
    async def process_event(self, event: Event) -> dict: ...

    @abstractmethod
    async def replay(self, workflow_id: str) -> dict: ...


class CustomOrchestrationAdapter(OrchestrationAdapter):
    def __init__(self, orchestrator: Orchestrator) -> None:
        self.orchestrator = orchestrator

    async def process_event(self, event: Event) -> dict:
        return await self.orchestrator.process_event(event)

    async def replay(self, workflow_id: str) -> dict:
        return await self.orchestrator.replay(workflow_id)


class TemporalOrchestrationAdapter(OrchestrationAdapter):
    """Temporal boundary placeholder.

    Contract is intentionally stable so a real Temporal workflow/activity
    implementation can be dropped in without changing API handlers.
    """

    def __init__(self) -> None:
        raise RuntimeError("Temporal orchestration is not production-ready in this build. Use ORCHESTRATION_ENGINE=custom.")

    async def process_event(self, event: Event) -> dict:
        raise RuntimeError("Temporal orchestration is not production-ready in this build. Use ORCHESTRATION_ENGINE=custom.")

    async def replay(self, workflow_id: str) -> dict:
        raise RuntimeError("Temporal orchestration is not production-ready in this build. Use ORCHESTRATION_ENGINE=custom.")
