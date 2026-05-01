"""
Seed demo workflows with realistic conversation histories and decision traces.

This script populates the database with sample workflows so the console
dashboard has visible state immediately on startup without manual event ingestion.

Run after initializing the database:
    python scripts/seed_demo_data.py

Safe to run multiple times (uses upsert semantics).
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4
import json

from sqlalchemy import text

from infra.db import Database
from infra.settings import settings


DEMO_WORKFLOWS = [
    {
        "workflow_id": "demo-w-001",
        "user_id": "cust-001",
        "state": "resolved",
        "outstanding_amount": 650.0,
        "negotiated_amount": 500.0,
        "strike_count": 0,
        "last_message": "Great, I can do $500 this month",
        "history_summary": "Customer offered payment after 2 payment follow-ups",
        "prompt_version": "extractor_v1",
        "policy_version": "policy_v1",
        "context_version": "ctx_v1",
        "autonomy_level": "full_auto",
    },
    {
        "workflow_id": "demo-w-002",
        "user_id": "cust-002",
        "state": "negotiating",
        "outstanding_amount": 1200.0,
        "negotiated_amount": None,
        "strike_count": 1,
        "last_message": "I'm facing hardship due to job loss",
        "history_summary": "Customer claimed hardship, currently awaiting verification",
        "prompt_version": "extractor_v1",
        "policy_version": "policy_v1",
        "context_version": "ctx_v1",
        "autonomy_level": "human_review",
    },
    {
        "workflow_id": "demo-w-003",
        "user_id": "cust-003",
        "state": "escalated",
        "outstanding_amount": 800.0,
        "negotiated_amount": None,
        "strike_count": 2,
        "last_message": "This is ridiculous, I'm not paying",
        "history_summary": "Customer became abusive, escalated for manual handling",
        "prompt_version": "extractor_v1",
        "policy_version": "policy_v1",
        "context_version": "ctx_v1",
        "autonomy_level": "blocked",
    },
    {
        "workflow_id": "demo-w-004",
        "user_id": "cust-004",
        "state": "waiting_for_payment",
        "outstanding_amount": 450.0,
        "negotiated_amount": 400.0,
        "strike_count": 0,
        "last_message": "I'll pay on Friday when I get paid",
        "history_summary": "Customer committed to $400 payment by Friday",
        "prompt_version": "extractor_v1",
        "policy_version": "policy_v1",
        "context_version": "ctx_v1",
        "autonomy_level": "full_auto",
    },
    {
        "workflow_id": "demo-w-005",
        "user_id": "cust-005",
        "state": "payment_failed",
        "outstanding_amount": 900.0,
        "negotiated_amount": 750.0,
        "strike_count": 1,
        "last_message": "Card was declined, trying different card tomorrow",
        "history_summary": "Payment attempt failed, customer working on resolution",
        "prompt_version": "extractor_v1",
        "policy_version": "policy_v1",
        "context_version": "ctx_v1",
        "autonomy_level": "human_review",
    },
]

DEMO_EVENTS = [
    {
        "workflow_id": "demo-w-001",
        "event_type": "user_message",
        "channel": "sms",
        "payload": {
            "user_id": "cust-001",
            "message": "Hi, can I get a payment plan?",
            "outstanding_amount": 650.0,
        },
        "occurred_at": datetime.now(UTC) - timedelta(hours=2),
    },
    {
        "workflow_id": "demo-w-001",
        "event_type": "user_message",
        "channel": "sms",
        "payload": {
            "user_id": "cust-001",
            "message": "I can do $500 this month",
            "outstanding_amount": 650.0,
        },
        "occurred_at": datetime.now(UTC) - timedelta(hours=1),
    },
    {
        "workflow_id": "demo-w-002",
        "event_type": "user_message",
        "channel": "email",
        "payload": {
            "user_id": "cust-002",
            "subject": "Payment issue - hardship",
            "body": "I lost my job last week and can't pay right now",
            "outstanding_amount": 1200.0,
        },
        "occurred_at": datetime.now(UTC) - timedelta(hours=3),
    },
    {
        "workflow_id": "demo-w-003",
        "event_type": "user_message",
        "channel": "sms",
        "payload": {
            "user_id": "cust-003",
            "message": "This is ridiculous, I'm not paying anything",
            "outstanding_amount": 800.0,
        },
        "occurred_at": datetime.now(UTC) - timedelta(minutes=30),
    },
    {
        "workflow_id": "demo-w-004",
        "event_type": "user_message",
        "channel": "sms",
        "payload": {
            "user_id": "cust-004",
            "message": "I'll pay on Friday when I get paid",
            "outstanding_amount": 450.0,
        },
        "occurred_at": datetime.now(UTC) - timedelta(hours=4),
    },
    {
        "workflow_id": "demo-w-005",
        "event_type": "user_message",
        "channel": "voice",
        "payload": {
            "user_id": "cust-005",
            "transcript": "Card was declined, trying different card tomorrow",
            "outstanding_amount": 900.0,
        },
        "occurred_at": datetime.now(UTC) - timedelta(hours=5),
    },
]

DEMO_DECISION_TRACES = [
    {
        "workflow_id": "demo-w-001",
        "event_id": "demo-w-001-evt-1",
        "llm_output": {
            "intent": "PAYMENT_OFFER",
            "amount": 500.0,
            "confidence": 0.92,
            "contradictory": False,
            "reasoning": "Customer explicitly offered $500 as payment",
        },
        "policy_result": {
            "action": "accept",
            "rationale": "Offer is 77% of outstanding; within policy",
        },
        "final_action": "resolve",
        "prompt_version": "extractor_v1",
        "policy_version": "policy_v1",
        "model_name": "groq/mixtral-8x7b-32768",
        "confidence": 0.92,
        "tokens_used": 145,
        "cost_usd": 0.00043,
        "autonomy_level": "full_auto",
        "consistency_variance": 0.0,
    },
    {
        "workflow_id": "demo-w-002",
        "event_id": "demo-w-002-evt-1",
        "llm_output": {
            "intent": "HARDSHIP",
            "amount": None,
            "confidence": 0.88,
            "contradictory": False,
            "reasoning": "Customer reported job loss",
        },
        "policy_result": {
            "action": "escalate",
            "rationale": "Hardship claim requires verification",
        },
        "final_action": "escalate",
        "prompt_version": "extractor_v1",
        "policy_version": "policy_v1",
        "model_name": "groq/mixtral-8x7b-32768",
        "confidence": 0.88,
        "tokens_used": 168,
        "cost_usd": 0.00048,
        "autonomy_level": "human_review",
        "consistency_variance": 0.0,
    },
    {
        "workflow_id": "demo-w-003",
        "event_id": "demo-w-003-evt-1",
        "llm_output": {
            "intent": "ABUSIVE",
            "amount": None,
            "confidence": 0.96,
            "contradictory": False,
            "reasoning": "Hostile language indicating refusal to cooperate",
        },
        "policy_result": {
            "action": "block",
            "rationale": "Policy violation: abusive conduct",
        },
        "final_action": "escalate",
        "prompt_version": "extractor_v1",
        "policy_version": "policy_v1",
        "model_name": "groq/mixtral-8x7b-32768",
        "confidence": 0.96,
        "tokens_used": 142,
        "cost_usd": 0.00042,
        "autonomy_level": "blocked",
        "consistency_variance": 0.0,
    },
    {
        "workflow_id": "demo-w-004",
        "event_id": "demo-w-004-evt-1",
        "llm_output": {
            "intent": "PAYMENT_COMMIT",
            "amount": 400.0,
            "confidence": 0.89,
            "contradictory": False,
            "reasoning": "Customer committed to $400 by Friday",
        },
        "policy_result": {
            "action": "wait",
            "rationale": "Commitment is credible; awaiting Friday",
        },
        "final_action": "wait",
        "prompt_version": "extractor_v1",
        "policy_version": "policy_v1",
        "model_name": "groq/mixtral-8x7b-32768",
        "confidence": 0.89,
        "tokens_used": 151,
        "cost_usd": 0.00045,
        "autonomy_level": "full_auto",
        "consistency_variance": 0.0,
    },
    {
        "workflow_id": "demo-w-005",
        "event_id": "demo-w-005-evt-1",
        "llm_output": {
            "intent": "PAYMENT_COMMIT",
            "amount": 750.0,
            "confidence": 0.85,
            "contradictory": False,
            "reasoning": "Customer committed to $750 with retry tomorrow",
        },
        "policy_result": {
            "action": "wait",
            "rationale": "Payment method issue; customer has recovery plan",
        },
        "final_action": "wait",
        "prompt_version": "extractor_v1",
        "policy_version": "policy_v1",
        "model_name": "cerebras/llama3.1-70b",
        "confidence": 0.85,
        "tokens_used": 156,
        "cost_usd": 0.00034,
        "autonomy_level": "human_review",
        "consistency_variance": 0.02,
    },
]

DEMO_ESCALATIONS = [
    {
        "workflow_id": "demo-w-002",
        "reason": "hardship_verification_required",
        "priority": 2,
        "sla_due_at": datetime.now(UTC) + timedelta(hours=24),
        "status": "open",
        "operator": None,
        "notes": "Customer claims job loss; verify income status before proceeding",
    },
    {
        "workflow_id": "demo-w-003",
        "reason": "abusive_conduct",
        "priority": 1,
        "sla_due_at": datetime.now(UTC) + timedelta(hours=2),
        "status": "open",
        "operator": None,
        "notes": "Customer used hostile language; hold escalation for manager review",
    },
]

DEMO_FEEDBACK = [
    {
        "workflow_id": "demo-w-001",
        "decision_id": "demo-w-001-evt-1",
        "signal_type": "agent_accuracy",
        "rating": 1,
        "notes": "Agent correctly identified payment offer and negotiated amount",
    },
    {
        "workflow_id": "demo-w-004",
        "decision_id": None,
        "signal_type": "customer_satisfaction",
        "rating": 4,
        "notes": "Customer appreciated flexible payment arrangement",
    },
]

DEMO_FAILURES = [
    {
        "workflow_id": "demo-w-005",
        "event_id": "demo-w-005-evt-1",
        "failure_type": "payment_method_error",
        "severity": "medium",
        "recoverability": "recoverable",
        "recovery_strategy": "customer_retry",
        "recovered": 0,
        "cost_impact_usd": 0.0,
        "notes": "Card decline; customer attempting alternative payment method",
    },
]


async def seed_demo_data() -> None:
    """Populate database with demo workflows and related data."""
    db = Database(settings.database_url)
    await db.init()

    async with db.engine.begin() as conn:
        now = datetime.now(UTC)

        # Seed workflows
        for wf_template in DEMO_WORKFLOWS:
            workflow = {
                **wf_template,
                "version": 1,
                "stale_after_hours": 48,
                "last_revalidated_at": None,
                "agreement_expires_at": now + timedelta(days=30) if wf_template["state"] == "waiting_for_payment" else None,
                "updated_at": now,
            }
            await db.upsert_workflow(workflow)

        # Seed events
        for evt_template in DEMO_EVENTS:
            event = {
                "event_id": f"{evt_template['workflow_id']}-{uuid4().hex[:8]}",
                "workflow_id": evt_template["workflow_id"],
                "event_type": evt_template["event_type"],
                "channel": evt_template["channel"],
                "payload": evt_template["payload"],
                "occurred_at": evt_template["occurred_at"],
                "idempotency_key": f"demo-idem-{evt_template['workflow_id']}-{uuid4().hex[:8]}",
                "schema_version": "v1",
            }
            # Check if already exists (idempotency)
            existing = await conn.execute(
                text("SELECT event_id FROM events WHERE workflow_id = :wid AND channel = :ch AND occurred_at = :oa"),
                {"wid": event["workflow_id"], "ch": event["channel"], "oa": event["occurred_at"]},
            )
            if not existing.first():
                await db.insert_event(event)

        # Seed decision traces
        for trace_template in DEMO_DECISION_TRACES:
            trace = {
                "decision_id": f"demo-trace-{uuid4().hex}",
                "workflow_id": trace_template["workflow_id"],
                "event_id": trace_template["event_id"],
                "llm_output": json.dumps(trace_template["llm_output"]),
                "policy_result": json.dumps(trace_template["policy_result"]),
                "final_action": trace_template["final_action"],
                "prompt_version": trace_template["prompt_version"],
                "policy_version": trace_template["policy_version"],
                "model_name": trace_template["model_name"],
                "confidence": trace_template["confidence"],
                "tokens_used": trace_template["tokens_used"],
                "cost_usd": trace_template["cost_usd"],
                "checksum": uuid4().hex,
                "autonomy_level": trace_template["autonomy_level"],
                "consistency_variance": trace_template.get("consistency_variance", 0.0),
                "failure_score": json.dumps({}),
                "critic_result": json.dumps({}),
                "tool_compensation_applied": 0,
                "created_at": now - timedelta(hours=1),
            }
            await db.insert_trace(trace)

        # Seed escalations
        for esc_template in DEMO_ESCALATIONS:
            escalation = {
                "escalation_id": f"demo-esc-{uuid4().hex}",
                "workflow_id": esc_template["workflow_id"],
                "reason": esc_template["reason"],
                "priority": esc_template["priority"],
                "sla_due_at": esc_template["sla_due_at"],
                "status": esc_template["status"],
                "operator": esc_template["operator"],
                "notes": esc_template["notes"],
            }
            existing = await conn.execute(
                text("SELECT escalation_id FROM escalations WHERE workflow_id = :wid AND reason = :r"),
                {"wid": escalation["workflow_id"], "r": escalation["reason"]},
            )
            if not existing.first():
                await conn.execute(
                    text("""INSERT INTO escalations 
                        (escalation_id, workflow_id, reason, priority, sla_due_at, status, operator, notes)
                        VALUES (:id, :wid, :r, :p, :sla, :s, :op, :n)"""),
                    {
                        "id": escalation["escalation_id"],
                        "wid": escalation["workflow_id"],
                        "r": escalation["reason"],
                        "p": escalation["priority"],
                        "sla": escalation["sla_due_at"],
                        "s": escalation["status"],
                        "op": escalation["operator"],
                        "n": escalation["notes"],
                    },
                )

        # Seed feedback signals
        for fb_template in DEMO_FEEDBACK:
            feedback = {
                "workflow_id": fb_template["workflow_id"],
                "decision_id": fb_template["decision_id"],
                "signal_type": fb_template["signal_type"],
                "rating": fb_template["rating"],
                "notes": fb_template["notes"],
                "created_at": now,
            }
            await conn.execute(
                text("""INSERT INTO feedback_signals 
                    (workflow_id, decision_id, signal_type, rating, notes, created_at)
                    VALUES (:wid, :did, :st, :r, :n, :ca)"""),
                {
                    "wid": feedback["workflow_id"],
                    "did": feedback["decision_id"],
                    "st": feedback["signal_type"],
                    "r": feedback["rating"],
                    "n": feedback["notes"],
                    "ca": feedback["created_at"],
                },
            )

        # Seed failure records
        for fail_template in DEMO_FAILURES:
            failure = {
                "workflow_id": fail_template["workflow_id"],
                "event_id": fail_template["event_id"],
                "failure_type": fail_template["failure_type"],
                "severity": fail_template["severity"],
                "recoverability": fail_template["recoverability"],
                "recovery_strategy": fail_template["recovery_strategy"],
                "recovered": fail_template["recovered"],
                "cost_impact_usd": fail_template["cost_impact_usd"],
                "notes": fail_template["notes"],
                "created_at": now,
            }
            await conn.execute(
                text("""INSERT INTO failure_records 
                    (workflow_id, event_id, failure_type, severity, recoverability, recovery_strategy, recovered, cost_impact_usd, notes, created_at)
                    VALUES (:wid, :eid, :ft, :s, :r, :rs, :rec, :ci, :n, :ca)"""),
                {
                    "wid": failure["workflow_id"],
                    "eid": failure["event_id"],
                    "ft": failure["failure_type"],
                    "s": failure["severity"],
                    "r": failure["recoverability"],
                    "rs": failure["recovery_strategy"],
                    "rec": failure["recovered"],
                    "ci": failure["cost_impact_usd"],
                    "n": failure["notes"],
                    "ca": failure["created_at"],
                },
            )

        # Seed borrower profiles
        demo_borrowers = [
            {"user_id": "cust-001", "risk_band": "low", "loan_segment": "personal", "outstanding_amount": 650.0, "dpd": 15, "prior_defaults": 0, "contact_attempts": 2, "preferred_channel": "sms", "dnc_flag": False, "legal_flag": False, "language": "en", "timezone": "Asia/Kolkata", "notes": "", "updated_at": now},
            {"user_id": "cust-002", "risk_band": "high", "loan_segment": "credit_card", "outstanding_amount": 1200.0, "dpd": 90, "prior_defaults": 1, "contact_attempts": 4, "preferred_channel": "email", "dnc_flag": False, "legal_flag": False, "language": "en", "timezone": "Asia/Kolkata", "notes": "", "updated_at": now},
            {"user_id": "cust-003", "risk_band": "critical", "loan_segment": "business", "outstanding_amount": 800.0, "dpd": 120, "prior_defaults": 3, "contact_attempts": 5, "preferred_channel": "voice", "dnc_flag": False, "legal_flag": True, "language": "en", "timezone": "Asia/Kolkata", "notes": "", "updated_at": now},
            {"user_id": "cust-dnc", "risk_band": "medium", "loan_segment": "personal", "outstanding_amount": 400.0, "dpd": 30, "prior_defaults": 0, "contact_attempts": 1, "preferred_channel": "sms", "dnc_flag": True, "legal_flag": False, "language": "en", "timezone": "Asia/Kolkata", "notes": "", "updated_at": now},
        ]
        
        for b in demo_borrowers:
            await conn.execute(
                text("""INSERT INTO borrower_profiles 
                    (user_id, risk_band, loan_segment, outstanding_amount, dpd, prior_defaults, contact_attempts, preferred_channel, dnc_flag, legal_flag, language, timezone, notes, updated_at)
                    VALUES (:u, :rb, :ls, :oa, :dpd, :pd, :ca, :pc, :dnc, :lf, :lang, :tz, :notes, :upd)
                    ON CONFLICT(user_id) DO NOTHING"""),
                {"u": b["user_id"], "rb": b["risk_band"], "ls": b["loan_segment"], "oa": b["outstanding_amount"], "dpd": b["dpd"], "pd": b["prior_defaults"], "ca": b["contact_attempts"], "pc": b["preferred_channel"], "dnc": b["dnc_flag"], "lf": b["legal_flag"], "lang": b["language"], "tz": b["timezone"], "notes": b["notes"], "upd": b["updated_at"]}
            )

    print("✓ Demo data seeded successfully")
    print("  - 5 workflows (resolved, negotiating, escalated, waiting, failed)")
    print("  - 6 events across workflows")
    print("  - 5 decision traces with real costs")
    print("  - 2 escalations (hardship, abusive)")
    print("  - 2 feedback signals")
    print("  - 1 failure record")
    print("\nConsole dashboard ready at: http://localhost:3000")


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
