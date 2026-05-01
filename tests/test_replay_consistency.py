from __future__ import annotations

from datetime import UTC, datetime

import pytest

from agents.llm_engine import LLMEngine
from agents.policy_engine import PolicyEngine
from domain.models import Event, EventType
from infra.db import Database
from workflow.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_replay_includes_reexecution_consistency() -> None:
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.init()
    orch = Orchestrator(db, LLMEngine(), PolicyEngine())

    events = [
        Event(
            event_id="rc1",
            workflow_id="rwc1",
            event_type=EventType.USER_MESSAGE,
            channel="sms",
            payload={"message": "I can pay 650", "user_id": "ru", "outstanding_amount": 700},
            occurred_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
            idempotency_key="rc-id-1",
        ),
        Event(
            event_id="rc2",
            workflow_id="rwc1",
            event_type=EventType.PAYMENT_WEBHOOK,
            channel="webhook",
            payload={"status": "paid", "user_id": "ru"},
            occurred_at=datetime(2026, 1, 1, 12, 1, 0, tzinfo=UTC),
            idempotency_key="rc-id-2",
        ),
    ]
    for e in events:
        await orch.process_event(e)

    replay = await orch.replay("rwc1")
    assert replay["status"] == "replay_ok"
    assert replay["reexecution_match"] is True
    assert replay["mismatch_index"] is None
