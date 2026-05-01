from __future__ import annotations

from agents.llm_engine import LLMEngine
from agents.policy_engine import PolicyEngine
from infra.db import Database
from infra.settings import settings
from workflow.adapter import CustomOrchestrationAdapter, OrchestrationAdapter, TemporalOrchestrationAdapter
from workflow.orchestrator import Orchestrator


def build_orchestration_adapter(db: Database) -> OrchestrationAdapter:
    engine = settings.orchestration_engine
    if engine == "temporal":
        return TemporalOrchestrationAdapter()
    orchestrator = Orchestrator(db=db, llm=LLMEngine(), policy=PolicyEngine())
    return CustomOrchestrationAdapter(orchestrator)
