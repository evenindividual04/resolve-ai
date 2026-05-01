from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest

from domain.models import Event, EventType
from infra.db import Database
from infra.queue import RedisEventQueue


def _env(name: str) -> str | None:
    v = os.getenv(name)
    return v if v else None


@pytest.mark.asyncio
async def test_postgres_roundtrip_if_configured() -> None:
    db_url = _env("INTEGRATION_DATABASE_URL")
    if not db_url:
        pytest.skip("integration database not configured")

    db = Database(db_url)
    await db.init()
    await db.upsert_workflow(
        {
            "workflow_id": "int-w1",
            "user_id": "int-u1",
            "state": "init",
            "outstanding_amount": 1000.0,
            "negotiated_amount": None,
            "strike_count": 0,
            "last_message": "",
            "history_summary": "",
            "version": 1,
            "prompt_version": "extractor_v2",
            "policy_version": "policy_v1",
            "updated_at": datetime.now(UTC),
        }
    )
    row = await db.get_workflow("int-w1")
    assert row is not None


@pytest.mark.asyncio
async def test_redis_stream_roundtrip_if_configured() -> None:
    redis_url = _env("INTEGRATION_REDIS_URL")
    if not redis_url:
        pytest.skip("integration redis not configured")

    q = RedisEventQueue(redis_url)
    await q.ensure_group()
    evt = Event(
        event_id="int-e1",
        workflow_id="int-w2",
        event_type=EventType.USER_MESSAGE,
        channel="sms",
        payload={"message": "pay 300", "user_id": "u", "outstanding_amount": 400},
        occurred_at=datetime.now(UTC),
        idempotency_key="int-id-1",
    )
    await q.publish(evt)
    batch = await q.read_batch(count=1, block_ms=50)
    assert len(batch) >= 1
    await q.ack(batch[0][0])
