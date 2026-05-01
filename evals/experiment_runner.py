from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from domain.models import LLMDecision

PromptPredictor = Callable[[str, float | None, str | None], LLMDecision]


def run_prompt_experiment(
    dataset: Sequence[dict[str, Any]],
    *,
    predictor: PromptPredictor,
    prompt_version: str,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    exact_matches = 0
    amount_matches = 0
    coverage = 0
    regressions: list[dict[str, Any]] = []

    for row in dataset:
        expected = dict(row["expected"])
        input_row = dict(row["input"])
        try:
            actual = predictor(input_row["text"], input_row.get("previous_commitment"), prompt_version)
            coverage += 1
            intent_match = actual.intent == expected.get("intent")
            amount_match = _amounts_match(expected.get("amount"), actual.amount)
            exact_match = intent_match and amount_match
            if exact_match:
                exact_matches += 1
            if amount_match:
                amount_matches += 1
            row_result = {
                "workflow_id": input_row.get("workflow_id"),
                "event_id": input_row.get("event_id"),
                "expected_intent": expected.get("intent"),
                "actual_intent": actual.intent,
                "expected_amount": expected.get("amount"),
                "actual_amount": actual.amount,
                "intent_match": intent_match,
                "amount_match": amount_match,
                "exact_match": exact_match,
                "prompt_version": prompt_version,
            }
            if not exact_match:
                regressions.append(row_result)
            rows.append(row_result)
        except Exception as exc:  # noqa: BLE001
            row_result = {
                "workflow_id": input_row.get("workflow_id"),
                "event_id": input_row.get("event_id"),
                "expected_intent": expected.get("intent"),
                "actual_intent": "ERROR",
                "expected_amount": expected.get("amount"),
                "actual_amount": None,
                "intent_match": False,
                "amount_match": False,
                "exact_match": False,
                "prompt_version": prompt_version,
                "error": str(exc),
            }
            regressions.append(row_result)
            rows.append(row_result)

    total_rows = len(dataset)
    return {
        "prompt_version": prompt_version,
        "total_rows": total_rows,
        "exact_match_rate": round(exact_matches / max(1, total_rows), 4),
        "amount_match_rate": round(amount_matches / max(1, total_rows), 4),
        "coverage_rate": round(coverage / max(1, total_rows), 4),
        "regressions": regressions,
        "rows": rows,
    }


def compare_prompt_versions(
    dataset: Sequence[dict[str, Any]],
    *,
    predictor: PromptPredictor,
    baseline_prompt_version: str,
    candidate_prompt_version: str,
) -> dict[str, Any]:
    baseline = run_prompt_experiment(dataset, predictor=predictor, prompt_version=baseline_prompt_version)
    candidate = run_prompt_experiment(dataset, predictor=predictor, prompt_version=candidate_prompt_version)
    return {
        "baseline": baseline,
        "candidate": candidate,
        "delta": {
            "exact_match_rate": round(candidate["exact_match_rate"] - baseline["exact_match_rate"], 4),
            "amount_match_rate": round(candidate["amount_match_rate"] - baseline["amount_match_rate"], 4),
            "coverage_rate": round(candidate["coverage_rate"] - baseline["coverage_rate"], 4),
            "regressions": len(candidate["regressions"]) - len(baseline["regressions"]),
        },
    }


def _amounts_match(expected_amount: Any, actual_amount: Any) -> bool:
    if expected_amount is None and actual_amount is None:
        return True
    if expected_amount is None or actual_amount is None:
        return False
    try:
        return abs(float(expected_amount) - float(actual_amount)) < 1e-6
    except Exception:  # noqa: BLE001
        return False