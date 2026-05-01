from __future__ import annotations

import importlib

import pytest

import infra.settings as settings_module
from workflow.adapter import TemporalOrchestrationAdapter


def test_settings_reject_unsupported_orchestration_engine(monkeypatch) -> None:
    monkeypatch.setenv("ORCHESTRATION_ENGINE", "temporal")

    with pytest.raises(ValueError, match="Unsupported ORCHESTRATION_ENGINE"):
        importlib.reload(settings_module)

    monkeypatch.setenv("ORCHESTRATION_ENGINE", "custom")
    importlib.reload(settings_module)


def test_temporal_adapter_is_explicitly_unsupported() -> None:
    with pytest.raises(RuntimeError, match="not production-ready"):
        TemporalOrchestrationAdapter()