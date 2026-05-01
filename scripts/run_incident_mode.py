from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import uuid4

from domain.models import IncidentType
from infra.db import Database


async def simulate_all(db_url: str = "sqlite+aiosqlite:///./agent.db") -> dict:
    db = Database(db_url)
    await db.init()
    runs = []
    for it in [IncidentType.DB_OUTAGE, IncidentType.QUEUE_DELAY, IncidentType.LLM_TIMEOUT, IncidentType.TOOL_FAILURE]:
        incident_id = str(uuid4())
        await db.insert_incident(
            {
                "incident_id": incident_id,
                "workflow_id": "incident-mode",
                "incident_type": it.value,
                "status": "simulated",
                "recovery_status": "degraded" if it in {IncidentType.DB_OUTAGE, IncidentType.QUEUE_DELAY} else "escalated",
                "details": {"source": "script"},
                "created_at": datetime.now(UTC),
            }
        )
        runs.append({"incident_id": incident_id, "incident_type": it.value})
    return {"simulated": len(runs), "runs": runs}


if __name__ == "__main__":
    import asyncio

    print(json.dumps(asyncio.run(simulate_all()), default=str))
