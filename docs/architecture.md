# Architecture: Autonomous Collections Intelligence Platform

## Overview

This system is a production-architecture simulation of an AI-native debt collections platform. It models the full complexity of real collections workflows with strict reliability, compliance, and auditability requirements.

The central question this system answers: **what does it take to trust an AI agent with ₹100Cr in loan recovery?**

---

## Why a State Machine, Not a Free-Form Agent

Most LLM agent frameworks give the model control over what action to take next. This is acceptable for productivity tools. It is unacceptable for regulated financial workflows.

**The problem with free-form agents in debt collection:**
- The LLM could contact a borrower who has filed DNC
- The LLM could promise a discount beyond policy limits
- The LLM could transition a workflow to an invalid state
- There is no deterministic audit trail

**Our solution:** A strict state machine in `workflow/transitions.py` defines the only valid state transitions. The LLM extracts a *signal* (intent + confidence). The *policy engine* decides what action to take. The state machine validates that the action is legal for the current state. The LLM never decides the action — it only classifies the input.

```
Borrower Message → LLMEngine.extract_intent() → BorrowerIntentSignal
                                                         ↓
                                              PolicyEngine.evaluate()
                                                         ↓
                                                    PolicyResult
                                                         ↓
                                              apply_transition(state, result)
                                                         ↓
                                              [Valid] → New WorkflowState
                                              [Invalid] → TransitionError → ESCALATED
```

---

## Why LLM is Used Only for Classification

The LLM in this system performs two tasks only:

1. **Intent extraction**: Given a borrower message, extract `{intent, amount, confidence, contradictory}` as structured JSON
2. **Response generation**: Given an action and borrower profile, generate a compliant outbound message

All consequential decisions — whether to accept an offer, compute a counter-offer, escalate, halt — are made by the `PolicyEngine` using deterministic logic. This is intentional.

**Why?** LLM outputs are stochastic. A model that sometimes says "offer acceptable" and sometimes says "escalate" for the same input is a reliability failure in a financial system. The `_evaluate_decision` method runs 3 parallel extractions and measures variance. If `variance > 0.34`, the intent is degraded to `UNKNOWN` and the workflow escalates rather than proceeding on an uncertain signal.

---

## BorrowerProfile: The Central Domain Entity

Every downstream decision in the system is shaped by the `BorrowerProfile`:

```
BorrowerProfile
├── risk_band: LOW | MEDIUM | HIGH | CRITICAL
├── loan_segment: PERSONAL | CREDIT_CARD | BUSINESS | GOLD | VEHICLE
├── dpd: int          # Days past due
├── prior_defaults: int
├── preferred_channel: WHATSAPP | SMS | EMAIL | VOICE
├── language: str     # For response localization
├── timezone: str     # For timezone-aware contact window enforcement
├── dnc_flag: bool    # Do Not Contact — hard gate on ALL contacts
└── legal_flag: bool  # Case referred to legal — immediate escalation
```

The `ProfileLoader` loads profiles deterministically from `user_id` for replay consistency. In production, this would fetch from a CRM via API.

**Why DNC is a hard gate, not a soft policy:**
In India, violating TRAI's Do Not Disturb registry is a regulatory offense. The DNC check fires in `Orchestrator.process_event()` *before* any LLM call. If `dnc_flag=True`, the workflow moves to `HALTED` and returns immediately. No LLM inference. No policy evaluation. No message sent.

---

## Negotiation Strategy

The `NegotiationStrategy` implements a risk-band × segment policy matrix for counter-offer computation:

| Segment | Risk Band | Min Fraction | Max Discount | Turn Budget |
|---|---|---|---|---|
| PERSONAL | LOW | 85% | 15% | 5 |
| PERSONAL | CRITICAL | 50% | 50% | 3 |
| BUSINESS | MEDIUM | 85% | 15% | 8 |
| CREDIT_CARD | HIGH | 70% | 30% | 3 |

**Concession curve:** The strategy starts at the minimum acceptable floor. For each turn beyond turn 2 without commitment, it concedes 5% of the floor — but never below the maximum discount hard floor. This is a deliberate, bounded concession curve, not random. It prevents the agent from either holding firm forever (borrower walks away) or conceding too fast (revenue loss).

**Anchoring detection:** If the borrower's prior offer is < 50% of the minimum acceptable floor, the system holds firm for 2 turns before any concession. Rewarding aggressive anchors with immediate concessions is economically irrational.

**Turn budget:** Each segment has a maximum number of turns. Business loans get 8 (relationship-oriented). Credit cards get 3-4 (high-volume, low-margin). Exceeding the budget triggers escalation.

---

## Compliance Layer

The `ComplianceGuard` filters all outbound messages before they are stored or delivered:

**Hard blocks (regex-based, no LLM):**
- Threat language: "police", "arrest", "FIR", "sue", "seize", "shame your family"
- PII leakage: Aadhaar (12 digits), PAN card pattern, credit card numbers
- Illegal amount promises: "waive your balance", "write off the loan"

**Why regex for hard blocks?** An LLM-based guard can miss exact violations. Regex is fast, deterministic, auditable, and testable. The guard runs on *every* outbound message, so it must be cheap. LLM-based soft checks (tone analysis) would run async and flag for review without blocking delivery.

**DNC check:** The guard enforces DNC at the message level as a second gate (the first gate is in the Orchestrator). Belt and suspenders.

---

## How Replay Enables Regulatory Audit

Every event, decision, and state change is persisted. The `replay()` function reconstructs the exact decision sequence from the event log alone:

1. Re-execute every event through the same LLM + policy pipeline
2. Compare the re-executed action sequence against stored traces
3. Compute SHA-256 hash of the event stream for tamper detection
4. Return `state_diff` showing any divergence between replayed and persisted state

**Why this matters:** A regulator can ask "why did the agent send this message to this borrower at this time?" The answer is: re-execute the event stream and you get the exact same decision. Every decision trace stores `prompt_version`, `policy_version`, `model_name`, `confidence`, `checksum`, and `autonomy_level`. This is a complete audit record.

---

## Channel Intelligence

The `ChannelRouter` selects the contact channel using:

1. **DNC gate**: Returns `"halt"` if `dnc_flag=True` — no channel selected
2. **Legal gate**: Returns `"halt"` if `legal_flag=True`
3. **Timezone-aware window**: Uses borrower's `timezone` field, not server UTC. A borrower in IST cannot be contacted at 3am just because the server is in UTC.
4. **Preferred channel**: Honoured for the first 2 attempts
5. **Escalation sequence**: WhatsApp → SMS → Email → Voice for subsequent attempts

**Why channel order matters:** WhatsApp has significantly higher open rates than SMS for borrowers under ₹1 lakh outstanding. Voice works better for elderly borrowers and large balances. The escalation sequence is a business decision encoded as policy, not hardcoded.

---

## Workflow Reliability

### Idempotency
Every event has an `idempotency_key`. The `insert_event()` method checks for duplicates before processing. Payment webhooks fire multiple times in production (UPI retries, gateway retries) — without idempotency, a single payment could be processed multiple times.

### Dead Letter Queue
Redis Streams consumer group with `max_retries=3` and exponential backoff. Events that exceed retries go to `negotiation:events:dlq` for manual inspection, not silent discard.

### Saga Compensation
Tool side-effects (payment link generation, user profile fetch) log `intent → success/failed → compensated`. If the tool fails mid-execution, the compensation record allows operators to identify partial executions that need manual resolution.

### Scheduler
A pure asyncio background task scans for:
- `WAITING_FOR_PAYMENT` workflows with expired `agreement_expires_at` → emits `SCHEDULER_TIMEOUT`
- `NEGOTIATING` workflows silent for 72+ hours → emits `SCHEDULER_TIMEOUT` for re-engagement

Idempotency keys on scheduler events (`timeout:{workflow_id}:{expiry}`) ensure the same timeout is never emitted twice.

---

## Observability

### Infrastructure metrics (`/metrics`)
Prometheus: `api_requests_total`, `api_request_latency_seconds`, `workflow_events_processed_total`

### Business metrics (`/metrics/business`)
What actually matters for a collections platform:
- `resolution_rate`: fraction of workflows that reach RESOLVED
- `escalation_rate`: fraction routed to human operators
- `avg_turns_to_close`: negotiation efficiency signal
- `cost_per_resolved_workflow`: LLM cost attribution per recovered loan
- `compliance_violations`: count of flagged outbound messages

### Decision traces
Every decision stores: `llm_output`, `policy_result`, `final_action`, `prompt_version`, `policy_version`, `model_name`, `confidence`, `tokens_used`, `cost_usd`, `checksum`, `autonomy_level`, `consistency_variance`. Full A/B testing of prompt or policy versions is possible by querying traces by `prompt_version`.

---

## What This Simulates vs What Is Stubbed

| Component | Status | Notes |
|---|---|---|
| State machine with transitions | ✅ Production-grade | Complete with compliance states |
| Event-driven ingestion | ✅ Production-grade | Redis Streams, idempotency, DLQ |
| LLM intent extraction | ✅ Production-grade | Multi-provider, async, consistency sampling |
| Policy engine | ✅ Production-grade | Segment-aware, DNC-enforced |
| Negotiation strategy | ✅ Production-grade | Risk matrix, anchoring detection, turn budget |
| Compliance guard | ✅ Production-grade | Regex hard-blocks, PII redaction |
| Responder + message log | ✅ Production-grade | LLM-generated, compliance-gated |
| Audit trail + replay | ✅ Production-grade | SHA-256 checksums, full replay |
| Workflow scheduler | ✅ Production-grade | asyncio, idempotent, DLQ-backed |
| Channel router | ✅ Production-grade | Timezone-aware, DNC-aware |
| Borrower profile | ✅ Stub CRM | Deterministic from user_id; replace with API call |
| Payment link | ✅ Stub | Returns mock URL; replace with payment gateway |
| WhatsApp/SMS delivery | 🔲 Stub | Channel = string; replace with Twilio/Meta API |
| Voice transcription | 🔲 Stub | transcript field in payload; replace with STT |
| ML-based risk scoring | 🔲 Not implemented | Currently rule-based; extend with model scores |
