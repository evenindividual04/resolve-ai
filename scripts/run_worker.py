from __future__ import annotations

import asyncio

from infra.db import Database
from infra.queue import RedisEventQueue, run_worker_loop
from infra.settings import settings
from workflow.factory import build_orchestration_adapter


async def main() -> None:
    db = Database(settings.database_url)
    await db.init()
    adapter = build_orchestration_adapter(db)
    queue = RedisEventQueue(settings.redis_url)

    async def handler(event):
        await adapter.process_event(event)

    await run_worker_loop(queue, handler)


if __name__ == "__main__":
    asyncio.run(main())
