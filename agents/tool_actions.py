from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolActionResult:
    tool: str
    payload: dict[str, Any]


class ToolActionEngine:
    def generate_payment_link(self, workflow_id: str, amount: float) -> ToolActionResult:
        return ToolActionResult(
            tool="generate_payment_link",
            payload={"workflow_id": workflow_id, "amount": amount, "url": f"https://pay.local/{workflow_id}?amount={amount:.2f}"},
        )

    def fetch_user_profile(self, user_id: str) -> ToolActionResult:
        return ToolActionResult(tool="fetch_user_profile", payload={"user_id": user_id, "segment": "standard"})

    def check_policy_snapshot(self) -> ToolActionResult:
        return ToolActionResult(tool="check_policy_snapshot", payload={"version": "policy_v1", "status": "active"})
