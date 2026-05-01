from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

from infra.db import Database
from infra.settings import settings


def label_from_feedback(signal_type: str, rating: int) -> str:
    if signal_type in {"bad_decision", "operator_override", "policy_gap"} or rating <= 2:
        return "negative"
    if signal_type == "good_decision" and rating >= 4:
        return "positive"
    return "neutral"


async def build_dataset(output_dir: Path) -> dict:
    db = Database(settings.database_url)
    await db.init()

    traces = await db.list_all_traces()
    feedback = await db.list_feedback()

    feedback_by_decision: dict[str, list[dict]] = {}
    feedback_by_workflow: dict[str, list[dict]] = {}
    for f in feedback:
        if f.get("decision_id"):
            feedback_by_decision.setdefault(str(f["decision_id"]), []).append(dict(f))
        feedback_by_workflow.setdefault(str(f["workflow_id"]), []).append(dict(f))

    output_dir.mkdir(parents=True, exist_ok=True)
    train_path = output_dir / "train.jsonl"
    eval_path = output_dir / "eval.jsonl"

    records: list[dict] = []
    for t in traces:
        fb = feedback_by_decision.get(str(t["decision_id"]), []) or feedback_by_workflow.get(str(t["workflow_id"]), [])
        if not fb:
            continue
        ratings = [int(x["rating"]) for x in fb]
        signal_types = [str(x["signal_type"]) for x in fb]
        label = label_from_feedback(signal_types[0], int(sum(ratings) / len(ratings)))

        records.append(
            {
                "workflow_id": t["workflow_id"],
                "decision_id": t["decision_id"],
                "input": t["llm_output"],
                "policy": t["policy_result"],
                "action": t["final_action"],
                "feedback": fb,
                "label": label,
                "created_at": str(t["created_at"]),
            }
        )

    split = int(len(records) * 0.8)
    train_records = records[:split]
    eval_records = records[split:]

    with train_path.open("w", encoding="utf-8") as f:
        for r in train_records:
            f.write(json.dumps(r, default=str) + "\n")

    with eval_path.open("w", encoding="utf-8") as f:
        for r in eval_records:
            f.write(json.dumps(r, default=str) + "\n")

    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "train_records": len(train_records),
        "eval_records": len(eval_records),
        "source_traces": len(traces),
        "source_feedback": len(feedback),
    }
    with (output_dir / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return summary


async def main() -> None:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = Path("artifacts") / "retraining" / stamp
    summary = await build_dataset(out)
    latest = Path("artifacts") / "retraining" / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    for name in ["train.jsonl", "eval.jsonl", "summary.json"]:
        (latest / name).write_text((out / name).read_text(encoding="utf-8"), encoding="utf-8")
    print(json.dumps({"output": str(out), **summary}))


if __name__ == "__main__":
    asyncio.run(main())
