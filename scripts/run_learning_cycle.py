from __future__ import annotations

import json
import subprocess
from pathlib import Path


def run() -> dict:
    proc = subprocess.run(["python", "scripts/build_retraining_dataset.py"], capture_output=True, text=True, check=True)
    result = json.loads(proc.stdout.strip())
    summary_path = Path("artifacts/retraining/latest/summary.json")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))

    # Lightweight promotion gate for retraining readiness.
    readiness = summary["train_records"] >= 20 and summary["eval_records"] >= 5
    report = {
        "dataset": result,
        "readiness": readiness,
        "next_action": "schedule_finetune" if readiness else "collect_more_feedback",
    }
    report_path = Path("artifacts/retraining/latest/readiness.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(run()))
