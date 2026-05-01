from __future__ import annotations

from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

import api.app as appmod


@pytest.mark.asyncio
async def test_events_endpoint_queue_mode(monkeypatch) -> None:
    async def fake_publish(event):
        return "1-0"

    monkeypatch.setattr(appmod.settings, "use_queue_ingest", True)
    monkeypatch.setattr(appmod.queue, "publish", fake_publish)

    transport = ASGITransport(app=appmod.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        evt = {
            "event_id": "qe1",
            "workflow_id": "qw1",
            "event_type": "user_message",
            "channel": "sms",
            "payload": {"message": "I can pay 500", "user_id": "u1", "outstanding_amount": 600},
            "occurred_at": datetime.now(UTC).isoformat(),
            "idempotency_key": "qid-1",
            "schema_version": "v1",
        }
        r = await client.post("/events", json=evt)
        assert r.status_code == 200
        assert r.json()["status"] == "queued"
