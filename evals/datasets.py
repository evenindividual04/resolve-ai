from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from domain.channels import normalize_channel_message


def build_prompt_eval_rows(source_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in source_rows:
        event = dict(row["event"])
        trace = dict(row["trace"])
        normalized = normalize_channel_message(event["channel"], event.get("payload", {}))
        rows.append(
            {
                "input": {
                    "text": normalized.text,
                    "channel": normalized.channel,
                    "workflow_id": event["workflow_id"],
                    "event_id": event["event_id"],
                    "previous_commitment": event.get("payload", {}).get("previous_commitment"),
                    "call_date_and_time": _isoformat(event.get("occurred_at")),
                },
                "expected": {
                    "intent": trace["llm_output"].get("intent", "UNKNOWN"),
                    "amount": trace["llm_output"].get("amount"),
                    "confidence": trace["llm_output"].get("confidence", 0.0),
                    "contradictory": trace["llm_output"].get("contradictory", False),
                },
                "metadata": {
                    "prompt_version": trace.get("prompt_version", "extractor_v1"),
                    "policy_version": trace.get("policy_version", "policy_v1"),
                    "model_name": trace.get("model_name", "unknown"),
                    "workflow_id": trace["workflow_id"],
                    "event_id": trace["event_id"],
                    "created_at": _isoformat(trace.get("created_at")),
                },
            }
        )
    return rows


def _isoformat(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)