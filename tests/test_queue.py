from __future__ import annotations

import json

import pytest

from domain.models import Event, EventType
from infra.queue import RedisEventQueue, StreamConfig


class FakeRedis:
    def __init__(self) -> None:
        self.store = []

    async def xgroup_create(self, **kwargs):
        return True

    async def xadd(self, stream, fields):
        msg_id = f"{len(self.store)+1}-0"
        self.store.append((msg_id, fields))
        return msg_id

    async def xreadgroup(self, **kwargs):
        return [(kwargs["streams"].keys().__iter__().__next__(), self.store)]

    async def xack(self, stream, group, msg_id):
        return 1


@pytest.mark.asyncio
async def test_queue_publish_read_ack() -> None:
    q = RedisEventQueue("redis://localhost:6379/0", StreamConfig())
    q.redis = FakeRedis()  # type: ignore[assignment]

    await q.ensure_group()
    event = Event(
        event_id="q1",
        workflow_id="wq1",
        event_type=EventType.USER_MESSAGE,
        channel="sms",
        payload={"message": "hello", "user_id": "u1", "outstanding_amount": 100},
        idempotency_key="qid-1",
    )
    msg_id = await q.publish(event)
    assert msg_id == "1-0"

    batch = await q.read_batch()
    assert len(batch) == 1
    assert batch[0][1].event_id == "q1"

    acked = await q.ack(batch[0][0])
    assert acked == 1
