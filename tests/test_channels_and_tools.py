from __future__ import annotations

from datetime import UTC, datetime

import pytest

from agents.llm_engine import LLMEngine
from agents.policy_engine import PolicyEngine
from domain.models import Event, EventType
from infra.db import Database
from workflow.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_email_channel_normalization_and_tools() -> None:
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.init()
    orch = Orchestrator(db, LLMEngine(), PolicyEngine())

    e = Event(
        event_id="ch1",
        workflow_id="chw1",
        event_type=EventType.USER_MESSAGE,
        channel="email",
        payload={"user_id": "u1", "outstanding_amount": 800, "subject": "payment", "body": "I can pay 700"},
        occurred_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
        idempotency_key="ch-id-1",
    )
    out = await orch.process_event(e)
    assert out["status"] == "processed"
    assert isinstance(out["side_effects"], list)
    assert any("version" in x for x in out["side_effects"])


@pytest.mark.asyncio
async def test_voice_channel_normalization() -> None:
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.init()
    orch = Orchestrator(db, LLMEngine(), PolicyEngine())

    e = Event(
        event_id="ch2",
        workflow_id="chw2",
        event_type=EventType.USER_MESSAGE,
        channel="voice",
        payload={"user_id": "u2", "outstanding_amount": 900, "transcript": "hardship emergency"},
        occurred_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
        idempotency_key="ch-id-2",
    )
    out = await orch.process_event(e)
    assert out["to"] in {"escalated", "contacted", "negotiating"}
