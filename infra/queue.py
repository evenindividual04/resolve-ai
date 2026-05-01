from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis

from domain.models import Event


@dataclass(frozen=True)
class StreamConfig:
    input_stream: str = "negotiation:events"
    dead_letter_stream: str = "negotiation:events:dlq"
    group: str = "workflow-workers"
    consumer: str = "worker-1"
    max_retries: int = 3
    retry_backoff_seconds: float = 0.5


class RedisEventQueue:
    def __init__(self, redis_url: str, cfg: StreamConfig | None = None) -> None:
        self.redis = Redis.from_url(redis_url, decode_responses=True)
        self.cfg = cfg or StreamConfig()

    async def ensure_group(self) -> None:
        try:
            await self.redis.xgroup_create(
                name=self.cfg.input_stream,
                groupname=self.cfg.group,
                id="0",
                mkstream=True,
            )
        except Exception as exc:  # BUSYGROUP or existing stream
            if "BUSYGROUP" not in str(exc):
                raise

    async def publish(self, event: Event) -> str:
        payload = {
            "event": event.model_dump(mode="json"),
            "retry_count": 0,
        }
        return await self.redis.xadd(self.cfg.input_stream, {"event": json.dumps(payload)})

    async def requeue(self, event: Event, retry_count: int) -> str:
        payload = {
            "event": event.model_dump(mode="json"),
            "retry_count": retry_count,
        }
        return await self.redis.xadd(self.cfg.input_stream, {"event": json.dumps(payload)})

    async def publish_dead_letter(self, event: Event, retry_count: int, error: str) -> str:
        payload = {
            "event": event.model_dump(mode="json"),
            "retry_count": retry_count,
            "error": error,
        }
        return await self.redis.xadd(self.cfg.dead_letter_stream, {"event": json.dumps(payload)})

    async def read_batch(self, count: int = 10, block_ms: int = 2000) -> list[tuple[str, Event, int]]:
        rows = await self.redis.xreadgroup(
            groupname=self.cfg.group,
            consumername=self.cfg.consumer,
            streams={self.cfg.input_stream: ">"},
            count=count,
            block=block_ms,
        )
        out: list[tuple[str, Event, int]] = []
        for _, entries in rows:
            for msg_id, fields in entries:
                envelope = json.loads(fields["event"])
                if "event" in envelope:
                    event_payload = envelope["event"]
                    retry_count = int(envelope.get("retry_count", 0))
                else:
                    # Backward compatibility for pre-envelope payloads.
                    event_payload = envelope
                    retry_count = 0
                out.append((msg_id, Event(**event_payload), retry_count))
        return out

    async def ack(self, message_id: str) -> int:
        return await self.redis.xack(self.cfg.input_stream, self.cfg.group, message_id)


async def run_worker_loop(queue: RedisEventQueue, handler) -> None:
    await queue.ensure_group()
    while True:
        batch = await queue.read_batch()
        if not batch:
            continue
        for msg_id, event, retry_count in batch:
            try:
                await handler(event)
                await queue.ack(msg_id)
            except Exception as exc:  # noqa: BLE001
                if retry_count >= queue.cfg.max_retries:
                    await queue.publish_dead_letter(event, retry_count=retry_count, error=str(exc))
                    await queue.ack(msg_id)
                    continue

                next_retry = retry_count + 1
                await asyncio.sleep(queue.cfg.retry_backoff_seconds * next_retry)
                await queue.requeue(event, retry_count=next_retry)
                await queue.ack(msg_id)
