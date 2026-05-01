from __future__ import annotations

from datetime import UTC, datetime

import pytest

from agents.llm_engine import LLMEngine
from domain.models import Event, EventType, LLMDecision
from evals.datasets import build_prompt_eval_rows
from evals.experiment_runner import compare_prompt_versions, run_prompt_experiment
from infra.db import Database


def test_build_prompt_eval_rows_from_traces() -> None:
    rows = build_prompt_eval_rows(
        [
            {
                "event": {
                    "event_id": "e1",
                    "workflow_id": "w1",
                    "channel": "sms",
                    "payload": {"message": "I can pay 500 now", "user_id": "u1"},
                    "occurred_at": datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
                },
                "trace": {
                    "decision_id": "d1",
                    "workflow_id": "w1",
                    "event_id": "e1",
                    "llm_output": {
                        "intent": "PAYMENT_OFFER",
                        "amount": 500,
                        "confidence": 0.92,
                        "contradictory": False,
                    },
                    "policy_result": {"next_action": "accept_offer"},
                    "final_action": "accept_offer",
                    "prompt_version": "extractor_v2",
                    "policy_version": "policy_v1",
                    "model_name": "llama-3.3-70b-versatile",
                    "confidence": 0.92,
                    "cost_usd": 0.00001,
                    "tokens_used": 42,
                    "checksum": "abc",
                    "autonomy_level": "full_auto",
                    "critic_result": {},
                    "consistency_variance": 0.0,
                    "failure_score": {},
                    "tool_compensation_applied": 0,
                    "created_at": datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
                },
            }
        ]
    )

    assert len(rows) == 1
    row = rows[0]
    assert row["input"]["text"] == "I can pay 500 now"
    assert row["expected"]["intent"] == "PAYMENT_OFFER"
    assert row["metadata"]["prompt_version"] == "extractor_v2"


@pytest.mark.asyncio
async def test_list_prompt_eval_rows_from_database() -> None:
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.init()
    event = Event(
        event_id="e2",
        workflow_id="w2",
        event_type=EventType.USER_MESSAGE,
        payload={"message": "hardship due to emergency", "user_id": "u2"},
        idempotency_key="idem-2",
    )
    await db.insert_event(event.model_dump())
    await db.insert_trace(
        {
            "decision_id": "d2",
            "workflow_id": "w2",
            "event_id": "e2",
            "llm_output": {"intent": "HARDSHIP", "amount": None, "confidence": 0.9, "contradictory": False},
            "policy_result": {"next_action": "escalate"},
            "final_action": "escalate",
            "prompt_version": "extractor_v2",
            "policy_version": "policy_v1",
            "model_name": "llama-3.3-70b-versatile",
            "confidence": 0.9,
            "cost_usd": 0.00001,
            "tokens_used": 33,
            "checksum": "def",
            "autonomy_level": "human_review",
            "critic_result": {},
            "consistency_variance": 0.0,
            "failure_score": {},
            "tool_compensation_applied": 0,
            "created_at": datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        }
    )

    rows = await db.list_prompt_eval_rows(prompt_version="extractor_v2")
    assert len(rows) == 1
    assert rows[0]["event"]["event_id"] == "e2"
    assert rows[0]["trace"]["prompt_version"] == "extractor_v2"


def test_prompt_experiment_runner_reports_regression() -> None:
    dataset = [
        {
            "input": {"text": "I can pay 500 now", "previous_commitment": None},
            "expected": {"intent": "PAYMENT_OFFER", "amount": 500.0},
            "metadata": {"prompt_version": "extractor_v2"},
        }
    ]

    class FakeEngine:
        def extract_intent(self, text: str, previous_commitment: float | None, prompt_version: str | None = None) -> LLMDecision:
            if prompt_version == "extractor_v1":
                return LLMDecision(intent="UNKNOWN", confidence=0.3, contradictory=False, prompt_version=prompt_version or "extractor_v1")
            return LLMDecision(intent="PAYMENT_OFFER", amount=500.0, confidence=0.95, contradictory=False, prompt_version=prompt_version or "extractor_v2")

    result = compare_prompt_versions(
        dataset,
        predictor=FakeEngine().extract_intent,
        baseline_prompt_version="extractor_v1",
        candidate_prompt_version="extractor_v2",
    )

    assert result["baseline"]["exact_match_rate"] == 0.0
    assert result["candidate"]["exact_match_rate"] == 1.0
    assert result["delta"]["exact_match_rate"] == 1.0
    assert result["delta"]["regressions"] == -1


def test_run_prompt_experiment_handles_candidate_output() -> None:
    dataset = [
        {
            "input": {"text": "I can pay 500 now", "previous_commitment": None},
            "expected": {"intent": "PAYMENT_OFFER", "amount": 500.0},
            "metadata": {"prompt_version": "extractor_v2"},
        },
        {
            "input": {"text": "This is a hardship", "previous_commitment": None},
            "expected": {"intent": "HARDSHIP", "amount": None},
            "metadata": {"prompt_version": "extractor_v2"},
        },
    ]

    def predictor(text: str, previous_commitment: float | None, prompt_version: str | None = None) -> LLMDecision:
        if "hardship" in text.lower():
            return LLMDecision(intent="HARDSHIP", confidence=0.9, contradictory=False, prompt_version=prompt_version or "extractor_v2")
        return LLMDecision(intent="PAYMENT_OFFER", amount=500.0, confidence=0.9, contradictory=False, prompt_version=prompt_version or "extractor_v2")

    result = run_prompt_experiment(dataset, predictor=predictor, prompt_version="extractor_v2")
    assert result["total_rows"] == 2
    assert result["exact_match_rate"] == 1.0
    assert result["coverage_rate"] == 1.0


def test_unknown_prompt_version_normalizes_to_default() -> None:
    engine = LLMEngine()

    assert engine._resolve_prompt_version("typo-version") == engine.prompts.default_extractor_version