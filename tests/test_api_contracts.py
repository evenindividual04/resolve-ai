from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from api.app import app, db


@pytest.mark.asyncio
async def test_api_contracts_end_to_end() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await db.init()

        evt = {
            "event_id": f"api-e1-{uuid4()}",
            "workflow_id": f"api-w1-{uuid4()}",
            "event_type": "user_message",
            "channel": "sms",
            "payload": {"message": "I can pay 700", "user_id": "u-api", "outstanding_amount": 800},
            "occurred_at": datetime.now(UTC).isoformat(),
            "idempotency_key": f"api-idem-{uuid4()}",
            "schema_version": "v1",
        }
        wid = evt["workflow_id"]
        r = await client.post("/events", json=evt)
        assert r.status_code == 200
        assert r.json()["status"] == "processed"

        wf = await client.get(f"/workflows/{wid}")
        assert wf.status_code == 200
        assert "workflow" in wf.json()

        tl = await client.get(f"/workflows/{wid}/timeline")
        assert tl.status_code == 200
        assert "events" in tl.json() and "decisions" in tl.json()

        rp = await client.post(f"/workflows/{wid}/replay", json={"workflow_id": wid})
        assert rp.status_code == 200
        assert rp.json()["status"] == "replay_ok"

        esc = await client.get("/escalations")
        assert esc.status_code == 200

        # no-op check path contract exists even if unknown ID
        act = await client.post(
            "/escalations/missing/actions",
            json={"operator": "ops1", "status": "in_progress", "notes": "triage"},
        )
        assert act.status_code == 404
