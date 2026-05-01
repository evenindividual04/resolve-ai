from __future__ import annotations

from datetime import UTC, datetime
import json
import sys

from pathlib import Path

import pytest

import scripts.run_learning_cycle as run_learning_cycle
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


def test_learning_cycle_uses_active_python(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    class _Result:
        stdout = json.dumps({"output": "artifacts/retraining/x", "train_records": 1, "eval_records": 0})

    def fake_run(cmd, capture_output, text, check):
        captured["cmd"] = cmd
        captured["capture_output"] = capture_output
        captured["text"] = text
        captured["check"] = check
        return _Result()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(run_learning_cycle.subprocess, "run", fake_run)

    latest = tmp_path / "artifacts" / "retraining" / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    (latest / "summary.json").write_text(
        json.dumps({"train_records": 1, "eval_records": 0}),
        encoding="utf-8",
    )

    report = run_learning_cycle.run()

    assert captured["cmd"][0] == sys.executable
    assert report["next_action"] == "collect_more_feedback"
