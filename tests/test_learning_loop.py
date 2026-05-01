from __future__ import annotations

from datetime import UTC, datetime

import pytest

from infra.db import Database


@pytest.mark.asyncio
async def test_feedback_storage_roundtrip() -> None:
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.init()
    await db.insert_feedback(
        {
            "workflow_id": "lw1",
            "decision_id": "d1",
            "signal_type": "policy_gap",
            "rating": 2,
            "notes": "missed edge case",
            "created_at": datetime.now(UTC),
        }
    )
    rows = await db.list_feedback("lw1")
    assert len(rows) == 1
    assert rows[0]["signal_type"] == "policy_gap"
