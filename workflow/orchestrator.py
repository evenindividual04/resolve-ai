from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

from agents.llm_engine import LLMEngine
from agents.negotiation_strategy import NegotiationStrategy
from agents.policy_engine import PolicyEngine
from agents.profile_loader import ProfileLoader
from agents.responder import Responder
from agents.tool_actions import ToolActionEngine
from domain.borrower import BorrowerProfile
from domain.channels import normalize_channel_message
from domain.models import (
    AutonomyLevel,
    DecisionTrace,
    Escalation,
    Event,
    EventType,
    FailureType,
    WorkflowState,
    WorkflowStatus,
)
from infra.db import Database
from workflow.context_builder import ContextBuilder
from workflow.transitions import TransitionError, apply_transition

log = logging.getLogger(__name__)


class Orchestrator:
    def __init__(self, db: Database, llm: LLMEngine, policy: PolicyEngine) -> None:
        self.db = db
        self.llm = llm
        self.policy = policy
        self.tools = ToolActionEngine()
        self.context_builder = ContextBuilder()
        self.profile_loader = ProfileLoader()
        self.negotiation = NegotiationStrategy()
        self.responder = Responder(llm)

    async def process_event(self, event: Event) -> dict:
        # Idempotency gate
        inserted = await self.db.insert_event(event.model_dump())
        if not inserted:
            return {"status": "duplicate", "event_id": event.event_id}

        state = await self._load_or_init_state(event)
        prev_state = state.current_state

        # Load borrower profile (deterministic from user_id for replay consistency)
        profile = self.profile_loader.load(state.user_id, state.outstanding_amount)

        # DNC / legal hard gate — before any LLM call
        if profile.dnc_flag:
            state.current_state = WorkflowStatus.HALTED
            await self.db.upsert_workflow(self._state_row(state))
            await self._record_failure(
                workflow_id=state.workflow_id,
                event_id=event.event_id,
                failure_type=FailureType.DNC_VIOLATION,
                severity="high",
                recoverability="low",
                recovery_strategy="escalate",
                recovered=False,
                notes="dnc_flag_active",
            )
            return {"status": "halted", "reason": "dnc_enforced", "workflow_id": state.workflow_id}

        # Clear per-event LLM cache
        self.llm.clear_cache()

        if self._is_stale(state, event):
            state.current_state = WorkflowStatus.REVALIDATION_REQUIRED

        decision, critic_result, consistency_variance, is_llm_call = await self._evaluate_decision(event, state)
        policy_result = self._policy_for_event(event, state, decision, profile)
        autonomy_level = self._autonomy_level(decision.confidence, critic_result, consistency_variance)

        if autonomy_level != AutonomyLevel.FULL_AUTO:
            policy_result.next_action = "escalate"
            policy_result.allowed = False
            policy_result.reason_code = "autonomy_guardrail"

        # Update negotiation tracking
        if decision.intent == "PAYMENT_OFFER" and decision.amount is not None:
            state.prior_offers = list(state.prior_offers) + [decision.amount]

        if decision.intent == "PAYMENT_OFFER" and policy_result.allowed:
            state.negotiated_amount = decision.amount
            state.agreement_expires_at = event.occurred_at + timedelta(hours=48)

        # Compute counter-offer amount for use by responder
        if policy_result.next_action == "counter_offer":
            state.counter_offer_amount = self.negotiation.compute_counter_offer(
                state.outstanding_amount,
                profile,
                state.turn_count,
                state.prior_offers,
            )

        # Increment turn count on negotiation-advancing events
        if event.event_type == EventType.USER_MESSAGE:
            state.turn_count += 1

        # Increment strike count on adverse signals
        if decision.intent in {"ABUSIVE", "CONFUSED"} or (
            event.event_type == EventType.PAYMENT_WEBHOOK
            and event.payload.get("status") != "paid"
        ):
            state.strike_count += 1

        state.last_message = str(event.payload.get("message", ""))
        state.history_summary = self._update_summary(state.history_summary, state.last_message)
        state.updated_at = event.occurred_at
        state.autonomy_level = autonomy_level
        state.version += 1

        if state.current_state == WorkflowStatus.REVALIDATION_REQUIRED and event.event_type == EventType.USER_MESSAGE:
            state.last_revalidated_at = event.occurred_at
            state.current_state = WorkflowStatus.NEGOTIATING

        try:
            state = apply_transition(state, policy_result)
        except TransitionError:
            state.current_state = WorkflowStatus.ESCALATED
            await self._record_failure(
                workflow_id=state.workflow_id,
                event_id=event.event_id,
                failure_type=FailureType.STATE_INCONSISTENCY,
                severity="high",
                recoverability="medium",
                recovery_strategy="escalate",
                recovered=True,
                notes="transition_error",
            )
            await self._create_escalation(state, "state_inconsistency")

        if policy_result.next_action == "escalate":
            await self._create_escalation(state, policy_result.reason_code)
            await self._record_failure(
                workflow_id=state.workflow_id,
                event_id=event.event_id,
                failure_type=FailureType.USER_AMBIGUITY if decision.intent in {"UNKNOWN", "CONFUSED"} else FailureType.POLICY_VIOLATION,
                severity="medium",
                recoverability="high",
                recovery_strategy="escalate",
                recovered=True,
                notes=policy_result.reason_code,
            )

        side_effects, tool_compensation_applied = await self._tool_side_effects(state, decision.intent)

        # Generate and store outbound message
        outbound_message = None
        if event.event_type in {EventType.USER_MESSAGE, EventType.SCHEDULER_TIMEOUT}:
            msg_log, guard_result = await self.responder.generate(policy_result.next_action, state, profile)
            try:
                await self.db.insert_message_log(msg_log.to_dict())
            except Exception:  # noqa: BLE001
                log.warning("message_log_insert_failed workflow_id=%s", state.workflow_id)
            outbound_message = {"content": msg_log.content, "channel": msg_log.channel, "compliance_passed": guard_result.passed}

        trace = self._decision_trace(
            event,
            state,
            decision.model_dump(),
            policy_result.model_dump(),
            autonomy_level=autonomy_level,
            critic_result=critic_result,
            consistency_variance=consistency_variance,
            tool_compensation_applied=tool_compensation_applied,
            is_llm_call=is_llm_call,
        )
        await self.db.insert_trace(trace.model_dump())
        await self.db.upsert_workflow(self._state_row(state))

        return {
            "status": "processed",
            "workflow_id": state.workflow_id,
            "from": prev_state,
            "to": state.current_state,
            "reason_code": policy_result.reason_code,
            "cost_usd": trace.cost_usd,
            "tokens_used": trace.tokens_used,
            "is_llm_call": is_llm_call,
            "side_effects": side_effects,
            "autonomy_level": autonomy_level,
            "consistency_variance": consistency_variance,
            "turn_count": state.turn_count,
            "strike_count": state.strike_count,
            "counter_offer_amount": state.counter_offer_amount,
            "outbound_message": outbound_message,
            "borrower_segment": profile.loan_segment.value,
            "borrower_risk_band": profile.risk_band.value,
        }

    async def replay(self, workflow_id: str) -> dict:
        events = await self.db.list_events(workflow_id)
        if not events:
            return {"workflow_id": workflow_id, "status": "no_events"}

        deterministic_hash = sha256()
        for evt in events:
            deterministic_hash.update(f"{evt['event_id']}|{evt['idempotency_key']}|{evt['event_type']}".encode())
        consistency = await self._reexecute_and_compare(workflow_id, events)

        return {
            "workflow_id": workflow_id,
            "event_count": len(events),
            "replay_digest": deterministic_hash.hexdigest(),
            "reexecution_match": consistency["match"],
            "mismatch_index": consistency["mismatch_index"],
            "state_match": consistency["state_match"],
            "state_diff": consistency["state_diff"],
            "status": "replay_ok",
        }

    async def _load_or_init_state(self, event: Event) -> WorkflowState:
        row = await self.db.get_workflow(event.workflow_id)
        if row:
            return WorkflowState(
                workflow_id=row["workflow_id"],
                user_id=row["user_id"],
                current_state=row["state"],
                outstanding_amount=row["outstanding_amount"],
                negotiated_amount=row["negotiated_amount"],
                counter_offer_amount=row.get("counter_offer_amount"),
                strike_count=row["strike_count"],
                turn_count=row.get("turn_count", 0),
                prior_offers=row.get("prior_offers") or [],
                last_message=row["last_message"],
                history_summary=row["history_summary"],
                version=row["version"],
                prompt_version=row["prompt_version"],
                policy_version=row["policy_version"],
                context_version=row.get("context_version", "ctx_v1"),
                autonomy_level=row.get("autonomy_level", AutonomyLevel.HUMAN_REVIEW),
                stale_after_hours=row.get("stale_after_hours", 48),
                last_revalidated_at=row.get("last_revalidated_at"),
                agreement_expires_at=row.get("agreement_expires_at"),
                updated_at=row["updated_at"],
            )

        return WorkflowState(
            workflow_id=event.workflow_id,
            user_id=str(event.payload.get("user_id", "unknown")),
            outstanding_amount=float(event.payload.get("outstanding_amount", 0.0)),
            current_state=WorkflowStatus.INIT,
        )

    async def _evaluate_decision(self, event: Event, state: WorkflowState) -> tuple:
        if event.event_type in {EventType.PAYMENT_WEBHOOK}:
            decision, _ = await self.llm.extract_intent("payment done", state.negotiated_amount)
            return decision, {"flags_issue": False}, 0.0, False

        if event.event_type in {EventType.SCHEDULER_TIMEOUT}:
            decision, _ = await self.llm.extract_intent("timeout reminder", state.negotiated_amount)
            return decision, {"flags_issue": False}, 0.0, False

        normalized = normalize_channel_message(event.channel, event.payload)
        self.context_builder.build(state, event)

        # Run primary extraction and 2 consistency samples concurrently.
        # This replaces the previous sequential 4-call pattern.
        results = await self.llm.extract_intent_multi(
            normalized.text,
            state.negotiated_amount,
            n=3,
        )
        primary_result, d1_result, d2_result = results
        primary, is_real_1 = primary_result
        d1, is_real_3 = d1_result
        d2, is_real_4 = d2_result
        is_real_any = is_real_1 or is_real_3 or is_real_4

        # Self-critique: if primary is uncertain, refine with explicit clarify prompt
        flags_issue = primary.intent in {"UNKNOWN", "CONFUSED"} or primary.confidence < 0.6
        refined = primary
        if flags_issue:
            refined, is_real_2 = await self.llm.extract_intent(
                f"clarify: {normalized.text}", state.negotiated_amount
            )
            is_real_any = is_real_any or is_real_2

        # Consistency check across 3 samples
        intents = [refined.intent, d1.intent, d2.intent]
        dominant = max(set(intents), key=intents.count)
        variance = 1.0 - (intents.count(dominant) / len(intents))

        if variance > 0.34:
            refined.intent = "UNKNOWN"
            refined.confidence = min(refined.confidence, 0.5)

        critic_result = {"flags_issue": flags_issue, "intents": intents, "dominant": dominant}
        return refined, critic_result, variance, is_real_any

    def _policy_for_event(self, event: Event, state: WorkflowState, decision, profile: BorrowerProfile | None = None):
        if event.event_type == EventType.PAYMENT_WEBHOOK:
            action = "resolve" if event.payload.get("status") == "paid" else "payment_failed"
            policy_result = self.policy.evaluate(
                decision=decision,
                outstanding_amount=state.outstanding_amount,
                now=event.occurred_at,
                profile=profile,
                strike_count=state.strike_count,
                turn_count=state.turn_count,
                prior_offers=state.prior_offers,
            )
            policy_result.next_action = action
            return policy_result
        return self.policy.evaluate(
            decision=decision,
            outstanding_amount=state.outstanding_amount,
            now=event.occurred_at,
            profile=profile,
            strike_count=state.strike_count,
            turn_count=state.turn_count,
            prior_offers=state.prior_offers,
        )

    @staticmethod
    def _autonomy_level(confidence: float, critic_result: dict, consistency_variance: float) -> AutonomyLevel:
        if consistency_variance > 0.34:
            return AutonomyLevel.BLOCKED
        if confidence >= 0.75 and not critic_result.get("flags_issue", False):
            return AutonomyLevel.FULL_AUTO
        if confidence >= 0.5:
            return AutonomyLevel.HUMAN_REVIEW
        return AutonomyLevel.BLOCKED

    @staticmethod
    def _is_stale(state: WorkflowState, event: Event) -> bool:
        e = event.occurred_at if event.occurred_at.tzinfo else event.occurred_at.replace(tzinfo=UTC)
        s = state.updated_at if state.updated_at.tzinfo else state.updated_at.replace(tzinfo=UTC)
        age_hours = (e - s).total_seconds() / 3600
        if state.agreement_expires_at:
            exp = state.agreement_expires_at if state.agreement_expires_at.tzinfo else state.agreement_expires_at.replace(tzinfo=UTC)
            if e > exp:
                return True
        # Negative age means out-of-order delivery (e.g. delayed webhook).
        # Log the anomaly but do not silently pass — treat as non-stale
        # so the event is still processed correctly.
        if age_hours < 0:
            log.warning(
                "out_of_order_event workflow_id=%s age_hours=%.2f event_id=unknown",
                state.workflow_id,
                age_hours,
            )
            return False
        return age_hours > state.stale_after_hours

    def _decision_trace(self, event: Event, state: WorkflowState, llm_output: dict, policy_result: dict, *, autonomy_level: AutonomyLevel, critic_result: dict, consistency_variance: float, tool_compensation_applied: bool, is_llm_call: bool) -> DecisionTrace:
        high_risk = policy_result["next_action"] in {"escalate", "counter_offer"}
        tokens, cost = self.llm.estimate_cost(str(event.payload), high_risk=high_risk)
        decision_id = str(uuid4())
        checksum = sha256(f"{decision_id}|{event.event_id}|{llm_output}|{policy_result}".encode()).hexdigest()
        failure_score = {
            "severity": "high" if autonomy_level == AutonomyLevel.BLOCKED else "medium",
            "recoverability": "high" if policy_result["next_action"] == "escalate" else "medium",
            "cost_impact": "low",
        }
        return DecisionTrace(
            decision_id=decision_id,
            workflow_id=state.workflow_id,
            event_id=event.event_id,
            llm_output=llm_output,
            policy_result=policy_result,
            final_action=policy_result["next_action"],
            prompt_version=state.prompt_version,
            policy_version=state.policy_version,
            model_name=self.llm.model_name,
            confidence=float(llm_output.get("confidence", 0.0)),
            tokens_used=tokens,
            cost_usd=cost,
            checksum=checksum,
            is_llm_call=is_llm_call,
            autonomy_level=autonomy_level,
            critic_result=critic_result,
            consistency_variance=consistency_variance,
            failure_score=failure_score,
            tool_compensation_applied=tool_compensation_applied,
        )

    async def _tool_side_effects(self, state: WorkflowState, intent: str) -> tuple[list[dict], bool]:
        effects: list[dict] = []
        compensated = False
        try:
            if intent == "PAYMENT_OFFER" and state.negotiated_amount is not None:
                await self.db.insert_tool_execution({
                    "workflow_id": state.workflow_id,
                    "tool_name": "generate_payment_link",
                    "status": "intent",
                    "payload": {"amount": state.negotiated_amount},
                    "created_at": datetime.now(UTC),
                })
                link = self.tools.generate_payment_link(state.workflow_id, state.negotiated_amount).payload
                effects.append(link)
                await self.db.insert_tool_execution({
                    "workflow_id": state.workflow_id,
                    "tool_name": "generate_payment_link",
                    "status": "success",
                    "payload": link,
                    "created_at": datetime.now(UTC),
                })

            if intent in {"HARDSHIP", "ABUSIVE"}:
                profile = self.tools.fetch_user_profile(state.user_id).payload
                effects.append(profile)

            snap = self.tools.check_policy_snapshot().payload
            effects.append(snap)
        except Exception as exc:  # noqa: BLE001
            compensated = True
            await self.db.insert_tool_execution({
                "workflow_id": state.workflow_id,
                "tool_name": "unknown",
                "status": "failed",
                "payload": {"error": str(exc)},
                "created_at": datetime.now(UTC),
            })
            await self.db.insert_tool_execution({
                "workflow_id": state.workflow_id,
                "tool_name": "compensation",
                "status": "compensated",
                "payload": {"reason": "partial_execution"},
                "created_at": datetime.now(UTC),
            })
        return effects, compensated

    async def _create_escalation(self, state: WorkflowState, reason: str) -> None:
        esc = Escalation(
            escalation_id=str(uuid4()),
            workflow_id=state.workflow_id,
            reason=reason,
            priority=1 if "abuse" in reason or "dnc" in reason else 2,
            sla_due_at=datetime.now(UTC) + timedelta(hours=4),
            notes=f"auto-generated from {state.current_state}",
        )
        await self.db.upsert_escalation(esc.model_dump())

    async def _record_failure(self, *, workflow_id: str, event_id: str | None, failure_type: FailureType, severity: str, recoverability: str, recovery_strategy: str, recovered: bool, notes: str) -> None:
        await self.db.insert_failure(
            {
                "workflow_id": workflow_id,
                "event_id": event_id,
                "failure_type": failure_type.value,
                "severity": severity,
                "recoverability": recoverability,
                "recovery_strategy": recovery_strategy,
                "recovered": 1 if recovered else 0,
                "cost_impact_usd": 0.0,
                "notes": notes,
                "created_at": datetime.now(UTC),
            }
        )

    async def _reexecute_and_compare(self, workflow_id: str, events: list[dict]) -> dict:
        traces = await self.db.list_traces(workflow_id)
        expected_actions = [t["final_action"] for t in traces]
        state: WorkflowState | None = None
        seen_actions: list[str] = []
        for idx, evt in enumerate(events):
            event = Event(**dict(evt))
            state = state or WorkflowState(
                workflow_id=event.workflow_id,
                user_id=str(event.payload.get("user_id", "unknown")),
                outstanding_amount=float(event.payload.get("outstanding_amount", 0.0)),
                current_state=WorkflowStatus.INIT,
            )
            profile = self.profile_loader.load(state.user_id, state.outstanding_amount)
            decision, critic_result, variance, _ = await self._evaluate_decision(event, state)
            policy_result = self._policy_for_event(event, state, decision, profile)
            autonomy = self._autonomy_level(decision.confidence, critic_result, variance)
            if autonomy != AutonomyLevel.FULL_AUTO:
                policy_result.next_action = "escalate"
            try:
                state = apply_transition(state, policy_result)
            except TransitionError:
                state.current_state = WorkflowStatus.ESCALATED
            seen_actions.append(policy_result.next_action)
            if idx < len(expected_actions) and seen_actions[idx] != expected_actions[idx]:
                return {"match": False, "mismatch_index": idx, "state_match": False, "state_diff": {"action_index": idx}}

        persisted = await self.db.get_workflow(workflow_id)
        if state is None or persisted is None:
            return {"match": False, "mismatch_index": None, "state_match": False, "state_diff": {"missing_state": True}}
        replay_row = self._state_row(state)
        keys = ["state", "outstanding_amount", "negotiated_amount", "strike_count", "history_summary"]
        diff = {}
        for k in keys:
            if replay_row.get(k) != persisted.get(k):
                diff[k] = {"expected": persisted.get(k), "replayed": replay_row.get(k)}
        return {"match": len(seen_actions) == len(expected_actions), "mismatch_index": None, "state_match": len(diff) == 0, "state_diff": diff}

    @staticmethod
    def _update_summary(summary: str, new_msg: str) -> str:
        """Semantic context compressor.

        Preserves the first 100 chars (initial hardship claim, first offer)
        and the last 350 chars (most recent context). The original rolling
        tail-only truncation lost the earliest context which caused the LLM
        to contradict earlier decisions it could no longer see.
        """
        combined = (summary + " | " + new_msg).strip(" |")
        if len(combined) <= 450:
            return combined
        head = combined[:100]
        tail = combined[-350:]
        return f"{head} [...] {tail}"

    @staticmethod
    def _state_row(state: WorkflowState) -> dict:
        row = state.model_dump()
        row["state"] = row.pop("current_state")
        return row
