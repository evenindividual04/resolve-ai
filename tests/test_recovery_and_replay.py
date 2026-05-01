from __future__ import annotations

from datetime import UTC, datetime

import pytest

from agents.llm_engine import LLMEngine
from agents.policy_engine import PolicyEngine
from domain.models import Event, EventType
from infra.db import Database
from workflow.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_crash_recovery_with_persistent_db(tmp_path) -> None:
    db_path = tmp_path / "recovery.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"

    db1 = Database(db_url)
    await db1.init()
    orch1 = Orchestrator(db1, LLMEngine(), PolicyEngine())

    e1 = Event(
        event_id="r1",
        workflow_id="rw1",
        event_type=EventType.USER_MESSAGE,
        channel="sms",
        payload={"message": "I can pay 600", "user_id": "ru1", "outstanding_amount": 700},
        occurred_at=datetime.now(UTC),
        idempotency_key="rid-1",
        schema_version="v1",
    )
    await orch1.process_event(e1)

    # Simulate process crash/restart with fresh orchestrator instance.
    db2 = Database(db_url)
    await db2.init()
    orch2 = Orchestrator(db2, LLMEngine(), PolicyEngine())

    e2 = Event(
        event_id="r2",
        workflow_id="rw1",
        event_type=EventType.USER_MESSAGE,
        channel="sms",
        payload={"message": "payment done", "user_id": "ru1", "outstanding_amount": 700},
        occurred_at=datetime.now(UTC),
        idempotency_key="rid-2",
        schema_version="v1",
    )
    out = await orch2.process_event(e2)
    assert out["status"] == "processed"

    state = await db2.get_workflow("rw1")
    assert state is not None
    assert state["version"] >= 2


@pytest.mark.asyncio
async def test_replay_is_deterministic_across_runs(tmp_path) -> None:
    db_path = tmp_path / "deterministic.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"
    db = Database(db_url)
    await db.init()
    orch = Orchestrator(db, LLMEngine(), PolicyEngine())

    events = [
        Event(
            event_id="d1",
            workflow_id="dw1",
            event_type=EventType.USER_MESSAGE,
            channel="sms",
            payload={"message": "I can pay 500", "user_id": "du1", "outstanding_amount": 700},
            occurred_at=datetime.now(UTC),
            idempotency_key="did-1",
            schema_version="v1",
        ),
        Event(
            event_id="d2",
            workflow_id="dw1",
            event_type=EventType.PAYMENT_WEBHOOK,
            channel="webhook",
            payload={"status": "paid", "user_id": "du1"},
            occurred_at=datetime.now(UTC),
            idempotency_key="did-2",
            schema_version="v1",
        ),
    ]
    for e in events:
        await orch.process_event(e)

    first = await orch.replay("dw1")
    second = await orch.replay("dw1")
    assert first["replay_digest"] == second["replay_digest"]
