"""Tests for WorkflowScheduler: event emission, idempotency, no double-fire."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from infra.scheduler import WorkflowScheduler


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.list_workflows_pending_timeout = AsyncMock(return_value=[])
    db.list_stale_negotiating_workflows = AsyncMock(return_value=[])
    return db


@pytest.fixture
def mock_queue():
    queue = MagicMock()
    queue.publish = AsyncMock(return_value="msg-id-1")
    return queue


@pytest.mark.asyncio
async def test_scheduler_emits_timeout_for_expired_agreement(mock_db, mock_queue):
    now = datetime.now(UTC)
    expired_at = (now - timedelta(hours=1)).isoformat()
    mock_db.list_workflows_pending_timeout.return_value = [
        {"workflow_id": "wf-001", "user_id": "u1", "agreement_expires_at": expired_at}
    ]

    scheduler = WorkflowScheduler(mock_db, mock_queue)
    await scheduler._scan_expired_agreements()

    mock_queue.publish.assert_called_once()
    event = mock_queue.publish.call_args[0][0]
    assert event.workflow_id == "wf-001"
    assert event.event_type.value == "scheduler_timeout"
    assert event.payload["reason"] == "agreement_expired"


@pytest.mark.asyncio
async def test_scheduler_timeout_idempotency_key_is_stable(mock_db, mock_queue):
    """Same workflow + expiry must produce same idempotency_key across invocations."""
    expiry = "2024-01-01T10:00:00+00:00"
    mock_db.list_workflows_pending_timeout.return_value = [
        {"workflow_id": "wf-002", "user_id": "u2", "agreement_expires_at": expiry}
    ]

    scheduler = WorkflowScheduler(mock_db, mock_queue)

    await scheduler._scan_expired_agreements()
    key1 = mock_queue.publish.call_args_list[0][0][0].idempotency_key

    await scheduler._scan_expired_agreements()
    key2 = mock_queue.publish.call_args_list[1][0][0].idempotency_key

    assert key1 == key2  # Same key = DB insert_event deduplication will prevent double-fire


@pytest.mark.asyncio
async def test_scheduler_emits_stale_negotiation_event(mock_db, mock_queue):
    updated_at = (datetime.now(UTC) - timedelta(hours=80)).isoformat()
    mock_db.list_stale_negotiating_workflows.return_value = [
        {"workflow_id": "wf-003", "user_id": "u3", "updated_at": updated_at, "stale_after_hours": 72}
    ]

    scheduler = WorkflowScheduler(mock_db, mock_queue)
    await scheduler._scan_stale_negotiations()

    mock_queue.publish.assert_called_once()
    event = mock_queue.publish.call_args[0][0]
    assert event.workflow_id == "wf-003"
    assert event.payload["reason"] == "stale_negotiation"


@pytest.mark.asyncio
async def test_scheduler_no_event_when_no_expired_workflows(mock_db, mock_queue):
    mock_db.list_workflows_pending_timeout.return_value = []
    scheduler = WorkflowScheduler(mock_db, mock_queue)
    await scheduler._scan_expired_agreements()
    mock_queue.publish.assert_not_called()
