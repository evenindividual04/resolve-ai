from __future__ import annotations

import json

import pytest
from httpx import ASGITransport, AsyncClient

import api.app as appmod


class _FakeProc:
    def __init__(self, payload: dict, code: int = 0):
        self.payload = payload
        self.returncode = code

    async def communicate(self):
        return json.dumps(self.payload).encode(), b""


@pytest.mark.asyncio
async def test_learning_endpoints(monkeypatch) -> None:
    async def fake_subprocess_exec(*args, **kwargs):
        if "build_retraining_dataset.py" in " ".join(args):
            return _FakeProc({"output": "artifacts/retraining/x", "train_records": 1, "eval_records": 0})
        return _FakeProc({"dataset": {"x": 1}, "readiness": False, "next_action": "collect_more_feedback"})

    monkeypatch.setattr(appmod.asyncio, "create_subprocess_exec", fake_subprocess_exec)

    transport = ASGITransport(app=appmod.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r1 = await client.post("/learning/retraining/build")
        assert r1.status_code == 200
        assert "train_records" in r1.json()

        r2 = await client.post("/learning/retraining/run")
        assert r2.status_code == 200
        assert "next_action" in r2.json()
