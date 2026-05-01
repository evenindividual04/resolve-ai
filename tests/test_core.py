from __future__ import annotations

from datetime import UTC, datetime

import pytest

from agents.llm_engine import LLMEngine
from agents.policy_engine import PolicyEngine
from domain.models import Event, EventType, WorkflowState, WorkflowStatus
from infra.db import Database
from workflow.orchestrator import Orchestrator
from workflow.transitions import TransitionError, apply_transition


@pytest.mark.asyncio
async def test_idempotent_event_processing() -> None:
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.init()
    orch = Orchestrator(db, LLMEngine(), PolicyEngine())

    event = Event(
        event_id="e1",
        workflow_id="w1",
        event_type=EventType.USER_MESSAGE,
        payload={"message": "I can pay 500", "user_id": "u1", "outstanding_amount": 600},
        idempotency_key="idem-1",
    )
    first = await orch.process_event(event)
    second = await orch.process_event(event)

    assert first["status"] == "processed"
    assert second["status"] == "duplicate"


@pytest.mark.asyncio
async def test_replay_digest_exists() -> None:
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.init()
    orch = Orchestrator(db, LLMEngine(), PolicyEngine())

    evt = Event(
        event_id="e2",
        workflow_id="w2",
        event_type=EventType.USER_MESSAGE,
        payload={"message": "hardship due to emergency", "user_id": "u2", "outstanding_amount": 800},
        idempotency_key="idem-2",
    )
    await orch.process_event(evt)
    replay = await orch.replay("w2")
    assert replay["status"] == "replay_ok"
    assert len(replay["replay_digest"]) == 64


@pytest.mark.asyncio
async def test_abuse_escalates() -> None:
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.init()
    orch = Orchestrator(db, LLMEngine(), PolicyEngine())
    evt = Event(
        event_id="e3",
        workflow_id="w3",
        event_type=EventType.USER_MESSAGE,
        payload={"message": "you are stupid", "user_id": "u3", "outstanding_amount": 900},
        idempotency_key="idem-3",
    )
    result = await orch.process_event(evt)
    assert result["to"] == WorkflowStatus.ESCALATED


def test_transition_rejects_illegal() -> None:
    state = WorkflowState(workflow_id="w", user_id="u", current_state=WorkflowStatus.RESOLVED)
    with pytest.raises(TransitionError):
        apply_transition(state, PolicyEngine().evaluate(decision=LLMEngine().extract_intent("I can pay 100", None), outstanding_amount=1000, now=datetime.now(UTC)))
