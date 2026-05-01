from __future__ import annotations

import asyncio

import pytest

from domain.models import Event, EventType
from infra.queue import RedisEventQueue, StreamConfig, run_worker_loop


class _FakeRedis:
    def __init__(self) -> None:
        self.stream_store: dict[str, list[tuple[str, dict]]] = {}

    async def xgroup_create(self, **kwargs):
        return True

    async def xadd(self, stream, fields):
        bucket = self.stream_store.setdefault(stream, [])
        msg_id = f"{len(bucket)+1}-0"
        bucket.append((msg_id, fields))
        return msg_id

    async def xreadgroup(self, **kwargs):
        stream = next(iter(kwargs["streams"].keys()))
        entries = self.stream_store.get(stream, [])
        if entries:
            msg = entries.pop(0)
            return [(stream, [msg])]
        return []

    async def xack(self, stream, group, msg_id):
        return 1


@pytest.mark.asyncio
async def test_worker_retries_then_dead_letters() -> None:
    cfg = StreamConfig(max_retries=2, retry_backoff_seconds=0)
    q = RedisEventQueue("redis://localhost:6379/0", cfg)
    q.redis = _FakeRedis()  # type: ignore[assignment]

    event = Event(
        event_id="qf1",
        workflow_id="wf1",
        event_type=EventType.USER_MESSAGE,
        channel="sms",
        payload={"message": "trigger fail", "user_id": "u1", "outstanding_amount": 100},
        idempotency_key="qid-f1",
    )
    await q.publish(event)

    async def always_fail(_event: Event):
        raise RuntimeError("boom")

    worker = asyncio.create_task(run_worker_loop(q, always_fail))
    await asyncio.sleep(0.02)
    worker.cancel()
    with pytest.raises(asyncio.CancelledError):
        await worker

    dlq = q.redis.stream_store.get(cfg.dead_letter_stream, [])  # type: ignore[attr-defined]
    assert len(dlq) == 1