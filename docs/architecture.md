# Architecture: Borrower Collections Intelligence System

## What This System Is Actually Doing

Before describing the components, it helps to describe what is actually happening when this system runs.

A borrower has an overdue loan. The institution needs to contact them, understand their situation, negotiate a repayment, and collect — without harassing them, violating regulatory constraints, or writing off more debt than necessary.

The system manages that interaction end-to-end:

1. A borrower sends a WhatsApp message. The orchestrator receives it as an event.
2. The LLM reads the message and produces a structured signal: `{ intent: HARDSHIP, confidence: 0.88, emotional_state: anxious, behavior_pattern: delaying }`.
3. The policy engine evaluates that signal against the borrower's profile — DPD, risk band, prior defaults, strike count. It decides: is this a genuine hardship or a stall tactic? Route to human review or offer EMI.
4. The state machine validates that this transition is legal from the current state.
5. The responder generates a compliant outbound message, gated by the compliance guard.
6. The channel router selects the best delivery channel given time of day, timezone, and what has worked before.
7. Everything is persisted: the event, the LLM output, the policy decision, the message sent, the state change.
8. If the borrower goes silent for 72 hours, the scheduler detects it and emits a re-engagement event.

The model participates in steps 2 and 5. Everything else is deterministic.

---

## The Central Question

What does it take to trust an AI agent with ₹100Cr in loan recovery?

Not model accuracy. Model accuracy is table stakes. The answer is: auditability, bounded failure paths, compliance enforcement that cannot be bypassed, and a system that fails safely rather than guessing forward when uncertain.

---

## Why a State Machine, Not a Free-Form Agent

LLM agent frameworks typically give the model control over what action to take next. This is fine for productivity tools where the cost of a wrong action is a slightly incorrect document.

In regulated financial workflows, the cost of a wrong action is a TRAI violation, a payment processed twice, or a message sent to a DNC-flagged borrower. None of these are recoverable at scale.

**The specific failure modes of free-form agents in collections:**
- The model contacts a borrower who has filed DNC — TRAI violation
- The model promises a settlement below the policy floor — direct revenue loss
- The model transitions a workflow to an invalid state — reconciliation error
- The model produces a different output on replay — audit fails

**The solution:** A strict state machine in `workflow/transitions.py` defines the only valid state transitions. The LLM produces a *signal*. The policy engine produces a *decision*. The state machine validates that the decision is legal. The LLM never decides what action to take — it only classifies the input.

```
Borrower Message
      ↓
LLMEngine.extract_intent()
      → { intent, amount, confidence, emotional_state, behavior_pattern }
      ↓
PolicyEngine.evaluate()
      → { allowed, reason_code, next_action, recommended_strategy }
      ↓
apply_transition(state, result)
      → [Valid]   New WorkflowState
      → [Invalid] TransitionError → ESCALATED
```

---

## Why the LLM Is Used Only for Classification

The LLM in this system does two things:

1. **Intent extraction:** Given a borrower message, produce `{ intent, amount, confidence, contradictory, emotional_state, behavior_pattern }` as structured JSON.
2. **Response generation:** Given an action, borrower profile, and active strategy, generate a compliant outbound message.

All consequential decisions — accept an offer, compute a counter-offer, escalate, halt — are made by the policy engine using deterministic logic.

**Why?** LLM outputs are stochastic. The same input can produce different outputs across calls. In a financial system, a decision that changes based on model sampling is not a decision — it's a guess. The `_evaluate_decision` method runs 3 parallel extractions and measures intent variance. If `variance > 0.34`, the intent is degraded to `UNKNOWN` and the workflow escalates. The system prefers escalation to uncertain autonomous action.

Additionally: LLM costs are real. Running expensive inference on every step of a high-volume collections workflow is economically irrational. The model is called for what only it can do — reading natural language and producing emotional signals. For everything else, the policy layer is cheaper, faster, and auditable.

---

## BorrowerProfile: The Central Domain Entity

Every downstream decision is shaped by the `BorrowerProfile`. Understanding why each field exists matters more than knowing what it contains.

```
BorrowerProfile
├── risk_band: LOW | MEDIUM | HIGH | CRITICAL
│     → Determines base discount floor and turn budget
│     → CRITICAL borrowers get shorter negotiations and lower discount ceilings
├── loan_segment: PERSONAL | CREDIT_CARD | BUSINESS | GOLD | VEHICLE
│     → Business loans warrant longer negotiations (relationship-oriented)
│     → Credit cards are high-volume, low-margin — shorter budgets
├── dpd: int
│     → Days past due. >90 DPD borrowers have very low repayment probability
│     → Used in risk scoring to adjust strategy selection
├── prior_defaults: int
│     → Each default compounds repayment probability downward
├── preferred_channel: WHATSAPP | SMS | EMAIL | VOICE
│     → Honoured for first 2 contact attempts
│     → Channel router escalates through sequence if no response
├── language: str
│     → Response generation uses this for localisation
├── timezone: str
│     → Contact window enforcement uses borrower's timezone, not server UTC
│     → A borrower in IST cannot be contacted at 3am because the server is in UTC
├── dnc_flag: bool
│     → Hard gate. Fires before any LLM call. No exceptions.
└── legal_flag: bool
      → Case referred to legal. Immediate escalation. No contact attempt.
```

The `ProfileLoader` loads deterministically from `user_id` to ensure replay produces the same profile as the original execution. In production, this is a CRM API call — the interface is identical.

**Why DNC is a hard gate, not a soft policy:**
Violating India's TRAI Do Not Disturb registry is a regulatory offense. The DNC check fires in `Orchestrator.process_event()` *before* any LLM inference, before any policy evaluation, before any message is generated. If `dnc_flag=True`, the workflow moves to `HALTED` and the function returns. There is no way for the LLM or policy engine to proceed past a DNC flag.

---

## Behavioural Intelligence

Collections is not about pressure. It's about understanding why a borrower is behaving the way they are and responding accordingly.

A borrower who is anxious and delaying because they genuinely lost their job should receive a different response than a borrower who is combative and anchoring aggressively because they think the institution will fold. Treating them identically produces worse outcomes for both.

The system tracks per-turn behavioural signals:

- **Emotional state:** `neutral`, `anxious`, `angry`, `cooperative` — extracted by the LLM
- **Behaviour pattern:** `compliant`, `delaying`, `unresponsive`, `combative` — extracted by the LLM
- **Repayment probability:** a deterministic score computed from `risk_band`, `dpd`, `prior_defaults`, `emotional_state`, `behavior_pattern`, and `strike_count`

These feed directly into strategy selection in the policy engine:

| Signal | Strategy | Negotiation Effect |
|---|---|---|
| Angry or combative | FIRM | Tighter discount floor, shorter turn budget, assertive tone |
| Anxious or hardship intent | EMPATHETIC | Wider EMI eligibility, more turns, softer generated language |
| Low repayment probability | FIRM | Hold position, escalate faster |
| Cooperative, normal engagement | PRAGMATIC | Standard bounds, concession curve active |

Strategy is selected deterministically. The LLM is told which strategy is active and adjusts its generated message tone accordingly. The model does not select strategy.

---

## Negotiation Strategy

The `NegotiationStrategy` implements a risk band × segment policy matrix. The matrix determines three parameters per borrower:

- **Minimum payment fraction:** The lowest offer the system will accept as a percentage of outstanding
- **Maximum discount fraction:** The absolute floor below which the system will not go regardless of turns
- **Turn budget:** How many rounds of negotiation are permitted before escalation

Example matrix (abbreviated):

| Segment | Risk Band | Min Fraction | Max Discount | Turn Budget |
|---|---|---|---|---|
| PERSONAL | LOW | 85% | 15% | 5 |
| PERSONAL | CRITICAL | 50% | 50% | 3 |
| BUSINESS | MEDIUM | 85% | 15% | 8 |
| CREDIT_CARD | HIGH | 70% | 30% | 3 |

**Concession curve:** The system starts at the minimum floor. For each turn beyond turn 2 without a commitment, it concedes 5% — but never below the maximum discount floor. This is deliberate and bounded. An agent that holds firm forever loses the borrower. An agent that concedes immediately loses revenue. The curve is the operational middle ground encoded as policy.

**Anchoring detection:** If the borrower's offer is below 50% of the minimum floor, the system holds for 2 turns before any concession. Rewarding aggressive anchoring with immediate movement is economically irrational and teaches borrowers to anchor harder.

**Turn budget by segment:** Business loans get 8 turns — relationship-oriented, higher stakes per account. Credit cards get 3-4 — high-volume, low-margin, faster resolution required. These are not arbitrary numbers; they reflect the economics of each segment.

**Strategy modifiers:** When the active strategy is FIRM, discount floors tighten. When EMPATHETIC, turn budgets extend and EMI eligibility widens. The matrix shifts based on strategy but is always bounded.

---

## Compliance Layer

The `ComplianceGuard` runs on every outbound message before it is stored or delivered. It operates in two modes:

**Hard blocks (regex, no LLM):**
- Threat language: `police`, `arrest`, `FIR`, `sue`, `seize`, `shame your family`
- PII leakage: Aadhaar (12 digits), PAN card pattern, credit card numbers
- Illegal promises: `waive your balance`, `write off the loan`

**Why regex for hard blocks, not an LLM:**
An LLM-based guard introduces the same non-determinism problem. It can miss exact violations. More importantly: the compliance guard runs on every message at high volume. Regex is sub-millisecond, deterministic, testable, and auditable. If a regulatory audit asks "what prevented threat language from being sent?", the answer needs to be a test-covered, inspectable function — not "the model didn't generate it."

**Belt and suspenders for DNC:** The compliance guard enforces DNC at the message level as a second check. The first is in the orchestrator before any processing. Both fire independently.

---

## How Replay Enables Regulatory Audit

Every event, decision, and state change is persisted. The replay function reconstructs the exact decision sequence from the event log alone:

1. Re-execute every event through the same LLM and policy pipeline
2. Compare the re-executed action sequence against stored decision traces
3. Compute SHA-256 hash of the event stream for tamper detection
4. Return `state_diff` showing any divergence between replayed and persisted state

**Why this matters operationally:** A regulator asks "why did the agent send this message to this borrower at 2pm on Tuesday?" The answer is not a guess — it is a re-execution that produces the same output, verified by checksum. Every decision trace stores `prompt_version`, `policy_version`, `model_name`, `confidence`, `checksum`, and `autonomy_level`. This is a complete, reproducible audit record.

**Why prompt versions are stored:** If a prompt change caused different behaviour across a period, the `prompt_version` field allows querying exactly which decisions were made under which prompt. A/B testing policy or prompt changes against real traces is a first-class capability.

---

## Channel Intelligence

The `ChannelRouter` selects the contact channel using:

1. **DNC gate:** Returns `halt` if `dnc_flag=True`
2. **Legal gate:** Returns `halt` if `legal_flag=True`
3. **Timezone-aware window:** Contact is gated to borrower local time using the `timezone` field
4. **Preferred channel:** Honoured for the first 2 attempts
5. **Success-rate routing:** Beyond attempt 2, the router picks the channel with the highest historical success rate for this borrower. If no historical data, falls back to escalation sequence.
6. **Escalation sequence:** WhatsApp → SMS → Email → Voice

**Why channel order matters:** WhatsApp has significantly higher open rates than SMS for sub-₹1 lakh outstanding. Voice works better for elderly borrowers and high-balance accounts. The sequence is a business decision encoded as policy. It is configurable — not hardcoded into the router logic.

---

## Workflow Reliability

Real collections systems encounter: duplicate webhook events, borrowers who go silent mid-negotiation, agents that time out mid-execution, payment links that fail to generate, databases that are unavailable for short windows, and queue workers that crash between consuming and processing a message.

Each failure mode has a defined handling path:

### Idempotency
Every event has an `idempotency_key`. The `insert_event()` method checks for duplicates before any processing. UPI payment webhooks fire multiple times — without idempotency, a single payment confirmation could process twice and produce two `RESOLVED` state transitions.

### Dead Letter Queue
Redis Streams consumer group with `max_retries=3` and exponential backoff. Events that exceed retries go to `negotiation:events:dlq`. No silent discard. Operators inspect the DLQ; events are replayable once the underlying issue is resolved.

### Saga Compensation
Tool side-effects — payment link generation, borrower profile fetches — log `intent → success/failed → compensated`. If a tool fails mid-execution, the compensation record identifies partial executions that need manual resolution. This is not full Saga pattern, but it gives operators the information they need to recover safely.

### Scheduler
A pure asyncio background task scans for two conditions:
- `WAITING_FOR_PAYMENT` workflows with expired `agreement_expires_at` → emits `SCHEDULER_TIMEOUT`
- `NEGOTIATING` workflows silent for 72+ hours → emits `SCHEDULER_TIMEOUT` for re-engagement

Idempotency keys on scheduler events (`timeout:{workflow_id}:{expiry}`) ensure the same timeout is never emitted twice, even if the scheduler runs in multiple processes.

---

## Observability

### Infrastructure metrics (`/metrics`)
Prometheus counters: `api_requests_total`, `api_request_latency_seconds`, `workflow_events_processed_total`.

### Business metrics (`/metrics/business`)
What actually matters for a collections platform:
- `resolution_rate`: fraction of workflows that reach RESOLVED
- `escalation_rate`: fraction routed to human operators
- `avg_turns_to_close`: negotiation efficiency signal — fewer turns = better agent and policy
- `cost_per_resolved_workflow`: LLM cost attribution per recovered loan
- `compliance_violations`: count of flagged outbound messages (should be zero in production)

### Decision traces
Every decision stores: `llm_output`, `policy_result`, `final_action`, `prompt_version`, `policy_version`, `model_name`, `confidence`, `tokens_used`, `cost_usd`, `checksum`, `autonomy_level`, `consistency_variance`. Querying by `prompt_version` gives a full A/B comparison of any prompt change against real production decisions.

---

## What Is Production-Grade vs What Is Stubbed

| Component | Status | Notes |
|---|---|---|
| State machine with transitions | ✅ Production-grade | Complete with compliance states, TransitionError handling |
| Event-driven ingestion | ✅ Production-grade | Redis Streams, idempotency, DLQ, retry with backoff |
| LLM intent extraction | ✅ Production-grade | Multi-provider, consistency sampling, critic pass, fallback |
| Policy engine | ✅ Production-grade | Segment-aware, DNC-enforced, strategy-aware |
| Behavioural intelligence | ✅ Production-grade | Emotional state, behaviour pattern, dynamic strategy selection |
| Negotiation strategy | ✅ Production-grade | Risk matrix, anchoring detection, turn budget, concession curve |
| Compliance guard | ✅ Production-grade | Regex hard-blocks, PII redaction, DNC second gate |
| Responder + message log | ✅ Production-grade | LLM-generated, strategy-aware tone, compliance-gated |
| Audit trail + replay | ✅ Production-grade | SHA-256 checksums, full replay, state diff |
| Workflow scheduler | ✅ Production-grade | asyncio, idempotent, DLQ-backed |
| Channel router | ✅ Production-grade | Timezone-aware, DNC-aware, success-rate-aware |
| Borrower profile | ⚙️ Stub CRM | Deterministic from `user_id`; replace with CRM API call |
| Payment link | ⚙️ Stub | Returns mock URL; replace with payment gateway (Razorpay, etc.) |
| WhatsApp/SMS delivery | 🔲 Stub | Channel is a string; replace with Twilio or Meta Cloud API |
| Voice transcription | 🔲 Stub | `transcript` field in payload; replace with STT pipeline |
| ML-based risk scoring | 🔲 Not implemented | Rule-based today; extend with XGBoost or custom model scores |
