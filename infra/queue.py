from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from redis.asyncio import Redis

from domain.models import Event


@dataclass(frozen=True)
class StreamConfig:
    input_stream: str = "negotiation:events"
    group: str = "workflow-workers"
    consumer: str = "worker-1"


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
        payload = event.model_dump(mode="json")
        return await self.redis.xadd(self.cfg.input_stream, {"event": json.dumps(payload)})

    async def read_batch(self, count: int = 10, block_ms: int = 2000) -> list[tuple[str, Event]]:
        rows = await self.redis.xreadgroup(
            groupname=self.cfg.group,
            consumername=self.cfg.consumer,
            streams={self.cfg.input_stream: ">"},
            count=count,
            block=block_ms,
        )
        out: list[tuple[str, Event]] = []
        for _, entries in rows:
            for msg_id, fields in entries:
                out.append((msg_id, Event(**json.loads(fields["event"]))))
        return out

    async def ack(self, message_id: str) -> int:
        return await self.redis.xack(self.cfg.input_stream, self.cfg.group, message_id)


async def run_worker_loop(queue: RedisEventQueue, handler) -> None:
    await queue.ensure_group()
    while True:
        batch = await queue.read_batch()
        for msg_id, event in batch:
            await handler(event)
            await queue.ack(msg_id)
