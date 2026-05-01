from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from agents.profile_loader import ProfileLoader
from domain.models import Event, EventType, WorkflowState, WorkflowStatus
from evals.borrower_simulator import BorrowerSimulator


class SimulationRunner:
    """Drives a complete multi-turn simulation of a collections workflow.

    Given an Orchestrator and a persona, runs N turns of the borrower-agent
    conversation and returns a structured report. Used in eval harness and
    integration tests to measure:
      - Resolution rate by persona
      - Escalation rate by persona
      - Average turns to close
      - LLM cost per simulation
      - Compliance violations generated
    """

    def __init__(self, orchestrator) -> None:
        self.orchestrator = orchestrator
        self.simulator = BorrowerSimulator()
        self.profile_loader = ProfileLoader()

    async def run(
        self,
        persona: str,
        outstanding_amount: float = 50000.0,
        max_turns: int = 10,
        workflow_id: str | None = None,
    ) -> dict[str, Any]:
        workflow_id = workflow_id or f"sim-{persona}-{uuid4().hex[:8]}"
        user_id = f"user-{persona}-{workflow_id}"
        profile = self.profile_loader.load_persona(user_id, persona, outstanding_amount)

        total_cost = 0.0
        turns_taken = 0
        events_processed: list[dict] = []
        final_state: str = WorkflowStatus.INIT.value

        # Seed the workflow with an initial contact event
        seed_event = Event(
            event_id=str(uuid4()),
            workflow_id=workflow_id,
            event_type=EventType.USER_MESSAGE,
            channel=profile.preferred_channel.value,
            payload={
                "user_id": user_id,
                "outstanding_amount": outstanding_amount,
                "message": "Hello, I received your notice.",
            },
            occurred_at=datetime.now(UTC),
            idempotency_key=f"seed:{workflow_id}:0",
        )
        result = await self.orchestrator.process_event(seed_event)
        events_processed.append({"turn": 0, "direction": "inbound", "result": result})
        total_cost += result.get("cost_usd", 0.0)
        final_state = result.get("to", WorkflowStatus.INIT.value)

        # Simulate up to max_turns borrower turns
        for turn in range(1, max_turns + 1):
            turns_taken = turn

            # Ghost persona: no response → simulate timeout after turn 2
            state_stub = WorkflowState(
                workflow_id=workflow_id,
                user_id=user_id,
                outstanding_amount=outstanding_amount,
                current_state=final_state,
            )
            message = self.simulator.generate_response(persona, state_stub, profile, turn)

            if message is None:
                # Ghost: no response, no further turns
                final_state = "timed_out"
                break

            event = Event(
                event_id=str(uuid4()),
                workflow_id=workflow_id,
                event_type=EventType.USER_MESSAGE,
                channel=profile.preferred_channel.value,
                payload={
                    "user_id": user_id,
                    "message": message,
                    "outstanding_amount": outstanding_amount,
                },
                occurred_at=datetime.now(UTC),
                idempotency_key=f"turn:{workflow_id}:{turn}",
            )
            result = await self.orchestrator.process_event(event)
            events_processed.append({"turn": turn, "message": message, "result": result})
            total_cost += result.get("cost_usd", 0.0)
            final_state = str(result.get("to", final_state))

            # Terminal states — stop simulation
            if final_state in {"resolved", "escalated", "halted"}:
                break

            # Liar: inject a payment commit webhook after turn 2 but don't pay
            if persona == "liar" and turn == 2:
                webhook = Event(
                    event_id=str(uuid4()),
                    workflow_id=workflow_id,
                    event_type=EventType.PAYMENT_WEBHOOK,
                    channel="system",
                    payload={"status": "failed", "reason": "insufficient_funds"},
                    occurred_at=datetime.now(UTC),
                    idempotency_key=f"webhook:{workflow_id}:failed",
                )
                wh_result = await self.orchestrator.process_event(webhook)
                events_processed.append({"turn": f"{turn}_webhook", "result": wh_result})
                total_cost += wh_result.get("cost_usd", 0.0)
                final_state = str(wh_result.get("to", final_state))

            # Cooperative: simulate successful payment after accept_offer
            if persona == "cooperative" and result.get("reason_code") == "offer_acceptable":
                webhook = Event(
                    event_id=str(uuid4()),
                    workflow_id=workflow_id,
                    event_type=EventType.PAYMENT_WEBHOOK,
                    channel="system",
                    payload={"status": "paid"},
                    occurred_at=datetime.now(UTC),
                    idempotency_key=f"webhook:{workflow_id}:paid",
                )
                wh_result = await self.orchestrator.process_event(webhook)
                events_processed.append({"turn": f"{turn}_webhook", "result": wh_result})
                total_cost += wh_result.get("cost_usd", 0.0)
                final_state = str(wh_result.get("to", final_state))
                break

        return {
            "workflow_id": workflow_id,
            "persona": persona,
            "outstanding_amount": outstanding_amount,
            "final_state": final_state,
            "turns_taken": turns_taken,
            "total_cost_usd": round(total_cost, 6),
            "resolved": final_state == "resolved",
            "escalated": final_state in {"escalated", "halted"},
            "events": events_processed,
        }
