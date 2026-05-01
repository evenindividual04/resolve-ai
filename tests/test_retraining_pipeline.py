from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from agents.llm_engine import LLMEngine
from agents.policy_engine import PolicyEngine
from domain.models import Event, EventType
from infra.db import Database
from workflow.orchestrator import Orchestrator
from scripts.build_retraining_dataset import build_dataset


@pytest.mark.asyncio
async def test_build_retraining_dataset(tmp_path: Path) -> None:
    db_path = tmp_path / "rt.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"
    db = Database(db_url)
    await db.init()

    orch = Orchestrator(db, LLMEngine(), PolicyEngine())
    evt = Event(
        event_id="rt1",
        workflow_id="rw1",
        event_type=EventType.USER_MESSAGE,
        channel="sms",
        payload={"message": "I can pay 600", "user_id": "u1", "outstanding_amount": 700},
        occurred_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
        idempotency_key="rt-id-1",
    )
    await orch.process_event(evt)

    traces = await db.list_traces("rw1")
    await db.insert_feedback(
        {
            "workflow_id": "rw1",
            "decision_id": traces[0]["decision_id"],
            "signal_type": "good_decision",
            "rating": 5,
            "notes": "correct",
            "created_at": datetime.now(UTC),
        }
    )

    # Temporarily run build against this DB by replacing settings at runtime.
    from infra import settings as settings_mod

    old = settings_mod.settings.database_url
    settings_mod.settings.database_url = db_url
    try:
        summary = await build_dataset(tmp_path / "out")
    finally:
        settings_mod.settings.database_url = old

    assert summary["train_records"] + summary["eval_records"] >= 1
    assert (tmp_path / "out" / "summary.json").exists()
