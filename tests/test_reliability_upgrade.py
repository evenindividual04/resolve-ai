from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from agents.llm_engine import LLMEngine
from agents.policy_engine import PolicyEngine
from domain.models import Event, EventType, IncidentType, WorkflowStatus
from infra.db import Database
from workflow.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_stale_state_revalidation_path() -> None:
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.init()
    orch = Orchestrator(db, LLMEngine(), PolicyEngine())

    seed = Event(
        event_id="s1",
        workflow_id="sw1",
        event_type=EventType.USER_MESSAGE,
        channel="sms",
        payload={"message": "I can pay 600", "user_id": "u1", "outstanding_amount": 700},
        occurred_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
        idempotency_key="sid-1",
    )
    await orch.process_event(seed)

    late = Event(
        event_id="s2",
        workflow_id="sw1",
        event_type=EventType.USER_MESSAGE,
        channel="sms",
        payload={"message": "back after delay", "user_id": "u1", "outstanding_amount": 700},
        occurred_at=datetime(2026, 1, 4, 12, 0, 0, tzinfo=UTC),
        idempotency_key="sid-2",
    )
    out = await orch.process_event(late)
    assert out["status"] == "processed"


@pytest.mark.asyncio
async def test_incident_and_failure_endpoints() -> None:
    import api.app as appmod

    transport = ASGITransport(app=appmod.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await appmod.db.init()
        inc = await client.post("/incidents/simulate", json={"incident_type": IncidentType.LLM_TIMEOUT.value, "workflow_id": "iw1", "payload": {}})
        assert inc.status_code == 200
        inc_id = inc.json()["incident_id"]

        detail = await client.get(f"/incidents/{inc_id}")
        assert detail.status_code == 200

        fs = await client.get("/failures/summary")
        assert fs.status_code == 200
        assert "total" in fs.json()


@pytest.mark.asyncio
async def test_economics_extended_fields() -> None:
    import api.app as appmod

    transport = ASGITransport(app=appmod.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await appmod.db.init()
        resp = await client.get("/economics/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "cost_per_resolution" in data
        assert "cost_per_failure" in data
        assert "model_breakdown" in data
