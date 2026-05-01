from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from domain.models import Event, EventType
from infra.db import Database
from infra.queue import RedisEventQueue

log = logging.getLogger(__name__)

_POLL_INTERVAL_SECONDS = 60  # How often to scan for expired workflows


class WorkflowScheduler:
    """Asyncio-based scheduler that emits timeout events for long-running workflows.

    Two scan types:
    1. Expired agreements: WAITING_FOR_PAYMENT workflows whose agreement_expires_at
       has passed. These borrowers committed but did not pay — we need to re-engage
       or escalate.

    2. Stale negotiations: NEGOTIATING workflows that haven't had any activity for
       stale_after_hours. These borrowers have gone silent mid-negotiation.

    Design: Pure asyncio — no Celery, no APScheduler dep. A single background Task
    is started in the FastAPI lifespan and cancelled on shutdown. Idempotency keys
    are derived from workflow_id + expiry timestamp so the same timeout is never
    emitted twice even if the scheduler restarts.
    """

    def __init__(self, db: Database, queue: RedisEventQueue) -> None:
        self.db = db
        self.queue = queue
        self._running = False

    async def start(self) -> asyncio.Task:
        self._running = True
        task = asyncio.create_task(self._poll_loop(), name="workflow-scheduler")
        log.info("workflow_scheduler_started poll_interval_s=%d", _POLL_INTERVAL_SECONDS)
        return task

    def stop(self) -> None:
        self._running = False

    async def _poll_loop(self) -> None:
        while self._running:
            try:
                await self._scan_expired_agreements()
                await self._scan_stale_negotiations()
            except Exception:  # noqa: BLE001
                log.exception("scheduler_poll_error")
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)

    async def _scan_expired_agreements(self) -> None:
        now = datetime.now(UTC)
        rows = await self.db.list_workflows_pending_timeout(now.isoformat())
        for row in rows:
            workflow_id = row["workflow_id"]
            expiry = row.get("agreement_expires_at", "")
            idempotency_key = f"timeout:{workflow_id}:{expiry}"
            event = Event(
                event_id=str(uuid4()),
                workflow_id=workflow_id,
                event_type=EventType.SCHEDULER_TIMEOUT,
                channel="system",
                payload={
                    "reason": "agreement_expired",
                    "agreement_expires_at": str(expiry),
                },
                occurred_at=now,
                idempotency_key=idempotency_key,
            )
            await self.queue.publish(event)
            log.info(
                "scheduler_timeout_emitted workflow_id=%s reason=agreement_expired",
                workflow_id,
            )

    async def _scan_stale_negotiations(self) -> None:
        # Use a conservative cutoff: 72 hours of silence in NEGOTIATING state
        cutoff = datetime.now(UTC) - timedelta(hours=72)
        rows = await self.db.list_stale_negotiating_workflows(cutoff.isoformat())
        for row in rows:
            workflow_id = row["workflow_id"]
            updated_at = row.get("updated_at", "")
            idempotency_key = f"stale:{workflow_id}:{updated_at}"
            event = Event(
                event_id=str(uuid4()),
                workflow_id=workflow_id,
                event_type=EventType.SCHEDULER_TIMEOUT,
                channel="system",
                payload={
                    "reason": "stale_negotiation",
                    "last_updated_at": str(updated_at),
                },
                occurred_at=datetime.now(UTC),
                idempotency_key=idempotency_key,
            )
            await self.queue.publish(event)
            log.info(
                "scheduler_timeout_emitted workflow_id=%s reason=stale_negotiation",
                workflow_id,
            )
