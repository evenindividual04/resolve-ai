from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from api.app import app, db


@pytest.mark.asyncio
async def test_metrics_economics_feedback_endpoints() -> None:
    await db.init()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        wid = f"obs-{uuid4()}"
        evt = {
            "event_id": f"obs-e-{uuid4()}",
            "workflow_id": wid,
            "event_type": "user_message",
            "channel": "sms",
            "payload": {"message": "I can pay 700", "user_id": "u-api", "outstanding_amount": 800},
            "occurred_at": datetime.now(UTC).isoformat(),
            "idempotency_key": f"obs-id-{uuid4()}",
            "schema_version": "v1",
        }
        ing = await client.post("/events", json=evt)
        assert ing.status_code == 200

        econ = await client.get("/economics/summary")
        assert econ.status_code == 200
        assert "total_cost_usd" in econ.json()

        fb = await client.post(
            "/feedback",
            json={"workflow_id": wid, "signal_type": "good_decision", "rating": 4, "notes": "solid"},
        )
        assert fb.status_code == 200

        fb_list = await client.get(f"/feedback?workflow_id={wid}")
        assert fb_list.status_code == 200
        assert len(fb_list.json()) >= 1

        metrics = await client.get("/metrics")
        assert metrics.status_code == 200
        assert "api_requests_total" in metrics.text
