from __future__ import annotations

import asyncio
from datetime import datetime

from agents.llm_engine import LLMEngine
from agents.policy_engine import PolicyEngine
from evals.red_team import generate_adversarial_cases


async def _run_eval_suite_async() -> dict:
    llm = LLMEngine()
    policy = PolicyEngine()
    outcomes: list[dict] = []
    fixed_eval_time = datetime(2026, 1, 1, 12, 0, 0)
    for c in generate_adversarial_cases():
        decision, _ = await llm.extract_intent(c.message, None)
        policy_result = policy.evaluate(decision=decision, outstanding_amount=1000, now=fixed_eval_time)
        outcomes.append({
            "label": c.label,
            "intent": decision.intent,
            "action": policy_result.next_action,
            "reason_code": policy_result.reason_code,
        })

    return {
        "cases": len(outcomes),
        "outcomes": outcomes,
    }


def run_eval_suite() -> dict:
    """Synchronous wrapper for the async eval suite. Runs via asyncio.run()."""
    return asyncio.run(_run_eval_suite_async())


if __name__ == "__main__":
    from pprint import pprint

    pprint(run_eval_suite())
