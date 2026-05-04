# Resolve AI — Borrower Collections Intelligence System

A production-architecture AI system for managing borrower interactions end-to-end: from first contact through negotiation, follow-up, payment commitment, and recovery — without a human in the loop unless one is required.

<p align="center">
  <video src="./video/out.mp4" controls width="100%" style="border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"></video>
</p>

The model is not the agent. The system is. LLMs are used to read borrower signals. Every consequential decision — what to offer, when to escalate, whether to contact at all — is made by the policy engine, not the model.

---

## Why This System Exists in the Real World

Debt collection is a coordination problem that breaks most software.

A borrower doesn't respond in a clean linear sequence. They go silent for 5 days, then message at 11pm claiming hardship, then make an offer they later retract, then default on a payment commitment. An agent managing this interaction can't just process one message at a time. It has to carry context across days, adapt strategy based on behaviour it has observed, and respond differently to a cooperative borrower than to an avoidant one.

**Why borrower behaviour breaks naive AI systems:**

Borrowers are irrational, inconsistent, and sometimes manipulative — not because they are bad actors, but because money stress produces non-rational behaviour. A system that takes messages at face value and extracts intent from them one at a time will fail immediately:

- A borrower offers ₹5,000 when the outstanding is ₹45,000. Is this a lowball anchor or genuine hardship? The answer requires knowing their repayment history, DPD, prior defaults, and what they said two days ago.
- A borrower says "I'll pay Friday." Three Fridays pass. Do you re-contact? When? On which channel? With what tone?
- A borrower claims job loss. Is this real? The system can't verify — but it can route to a human for review rather than blindly offering a waiver.

A language model cannot answer these questions reliably on its own. It introduces stochasticity into decisions that must be deterministic, reproducible, and auditable.

**Why deterministic workflows are required:**

Collections platforms operate under strict regulatory constraints — TRAI's DNC registry, RBI fair practices guidelines, state-level consumer protection law. A single violation (contacting a DNC-flagged borrower, threatening legal action through a message, sharing a borrower's data) can expose the institution to regulatory and legal risk.

You can't run a probabilistic agent over regulated financial workflows. You need hard gates that fire before any model inference. You need an audit trail that a regulator can inspect and re-execute. You need a system that fails safely when the model is uncertain, not one that guesses forward.

This system is the infrastructure layer that makes AI-driven collections trustworthy enough to run at scale.

---

## How This Maps to Real Debt Collection Systems

This is a prototype of the infrastructure stack a platform like Riverline runs in production.

Riverline operates AI agents that contact borrowers across WhatsApp, SMS, email, and voice. Those agents run long-running workflows — not single-turn conversations — that span days or weeks. They track borrower psychology, adapt negotiation strategy, enforce compliance in real time, and escalate to human operators with full context when the situation demands it.

This system implements the same architecture at production depth:

| Real Collections Problem | How This System Handles It |
|---|---|
| Borrower goes silent for days | Scheduler detects inactivity, emits re-engagement timeout event |
| Payment commitment expires | Agreement expiry tracked per-workflow; `SCHEDULER_TIMEOUT` triggers follow-up |
| Borrower claims hardship | LLM extracts hardship signal; policy routes to human review or EMI offer |
| Borrower becomes abusive | Intent classified as `ABUSIVE`; workflow escalated immediately, no further contact |
| DNC-flagged borrower contacted | Hard gate fires before LLM call; workflow halted, no message sent |
| Agent offers too high a discount | Policy engine caps discount at segment-specific floor; offer rejected |
| Same payment webhook fires 3x | Idempotency key deduplication; single execution guaranteed |
| Regulator asks for decision trail | Full event log + decision traces with SHA-256 checksums; replay to verify |
| Channel gets no response | Escalation sequence: preferred channel → WhatsApp → SMS → Email → Voice |
| Negotiation stalls for 8 turns | Turn budget exhausted; workflow escalates, operator reviews |

The agent layer is intentionally thin. Contact logic, channel selection, compliance enforcement, counter-offer calculation, and escalation routing are all deterministic. The model reads borrower language. The system acts.

---

## Why It Exists

Most AI agent frameworks are built for productivity tools: helpful, fast, occasionally wrong. That's acceptable when the cost of being wrong is a slightly bad calendar event.

In collections, the cost of a wrong decision is:
- contacting a borrower in a prohibited window (TRAI violation)
- offering a discount beyond the approved policy floor (revenue loss)
- sending an abusive-sounding message under the institution's name (compliance and reputational risk)
- processing a payment twice because a UPI webhook fired twice (financial reconciliation error)

This system is designed for the opposite of "occasionally wrong." Every decision is bounded by policy. Every action is logged. Every failure path has a defined resolution. Operators can replay any workflow and get the same output the live system produced.

---

## What It Does

This system manages the full borrower interaction lifecycle:

- **First contact:** Selects channel based on borrower profile, timezone, and DNC status. Generates a compliant outbound message.
- **Intent extraction:** Reads incoming borrower messages and extracts structured signals — payment offer, hardship claim, abusive language, confusion — using an LLM constrained to JSON output.
- **Negotiation:** Evaluates borrower offers against a policy matrix (risk band × loan segment). Computes counter-offers using a bounded concession curve. Tracks turns. Detects anchoring.
- **Behavioural tracking:** Tracks emotional state and behaviour pattern across turns. Adjusts strategy — Firm, Empathetic, or Pragmatic — based on how the borrower is engaging.
- **Follow-up:** Background scheduler detects stale workflows and payment commitment timeouts. Emits re-engagement events without operator intervention.
- **Escalation:** Routes to human operators with full context — reason code, decision history, SLA deadline — when the system cannot safely proceed autonomously.
- **Payment lifecycle:** Tracks commitment, generates payment link, processes webhook, detects failure, and re-engages.
- **Audit trail:** Every event, decision, and state change is persisted. Full replay with SHA-256 integrity checking.

---

## System Design

The system runs two execution paths. A message arrives from a borrower. Or a background scheduler determines that a borrower has gone silent.

In both cases, the execution sequence is:

```
Incoming message / timeout
         ↓
Orchestrator.process_event()
         ↓
DNC gate — halt immediately if flagged, no LLM call
         ↓
LLMEngine — extract intent signal (JSON): { intent, amount, confidence, emotional_state, behavior_pattern }
         ↓
PolicyEngine — evaluate signal against policy: { allowed, reason_code, next_action, recommended_strategy }
         ↓
AutonomyCheck — if confidence < threshold or variance > 0.34, escalate rather than proceed
         ↓
apply_transition() — validate state change is legal; escalate on illegal transition
         ↓
Responder — generate compliant outbound message, gated by ComplianceGuard
         ↓
ChannelRouter — select channel by borrower profile, success metrics, and timezone window
         ↓
Persist: event log, decision trace, message log, updated workflow state
```

The model touches two steps. Everything else is deterministic.

### Runtime Components

- **API (FastAPI):** Event ingestion, workflow queries, replay, economics, feedback, escalation, incidents, learning endpoints
- **Orchestrator:** Stateful coordination of every step above. Handles idempotency, stale state detection, tool side-effects, failure recording.
- **Policy Engine:** Compliance gates and business rules. Determines action. LLM output is an input here, not the output.
- **Negotiation Strategy:** Risk band × segment policy matrix. Bounded concession curve. Turn budgets. EMI eligibility. Dynamically adjusted by selected strategy type.
- **LLM Engine:** Multi-provider (Groq, Cerebras, Gemini), parallel consistency sampling, critic pass on uncertain decisions. Structured extraction only.
- **Channel Router:** Timezone-aware, DNC-aware, success-rate-aware channel selection.
- **Compliance Guard:** Regex hard-blocks for threat language, PII, and illegal promises. Runs on every outbound message before delivery.
- **Scheduler:** asyncio background task. Detects expired agreements and silent workflows. Emits re-engagement events with idempotency.
- **Storage:** PostgreSQL or SQLite for workflow state, events, traces; Redis Streams for async event queue with DLQ.
- **Ops Console (Next.js):** Operator triage interface. Workflows, escalations, message logs, decision ledger, economics, feedback.

### Execution Modes

- **Direct mode:** `POST /events` — processed synchronously in the API process. Simple deployments.
- **Queue mode:** `POST /events` — enqueued to Redis Streams. Worker consumes and processes. Production deployments.

---

## Borrower Lifecycle States

```
INIT → CONTACTED → NEGOTIATING → WAITING_FOR_PAYMENT → RESOLVED
                       ↓                  ↓
                   ESCALATED         PAYMENT_FAILED → NEGOTIATING (re-engage)
                       ↓
                    HALTED (DNC / legal flag)
```

State transitions are validated by a strict transition table. An invalid transition (e.g. `RESOLVED → NEGOTIATING`) throws a `TransitionError` that the orchestrator catches, logs, and escalates. The state machine cannot be bypassed.

---

## Behavioural Intelligence

Borrowers are not interchangeable. A borrower who has been cooperative across three turns and made a realistic offer should be handled differently than one who has been avoidant for a week and then sent a hostile message.

The system tracks:

- **Emotional state** per turn: `neutral`, `anxious`, `angry`, `cooperative`
- **Behaviour pattern**: `compliant`, `delaying`, `unresponsive`, `combative`
- **Repayment probability**: a score derived from risk band, DPD, prior defaults, emotional state, behaviour pattern, and strike count

These signals feed directly into strategy selection:

| Borrower Signal | Selected Strategy | Effect |
|---|---|---|
| Angry / combative | `FIRM` | Tighter discounts, shorter turn budget, formal tone |
| Anxious / hardship | `EMPATHETIC` | Wider EMI eligibility, more turns, softer language |
| Cooperative / normal | `PRAGMATIC` | Standard bounds, concession curve active |
| Low repayment probability | `FIRM` | Hold position, escalate faster |

Strategy selection is deterministic given inputs. The LLM adjusts its response tone to match. It does not decide the strategy.

---

## Product Capabilities

- Deterministic workflow state machine with policy-enforced transitions
- Adaptive behavioural intelligence: emotional state tracking, strategy selection, tone adaptation
- Full audit trail: every decision recorded with `prompt_version`, `policy_version`, `model_name`, `confidence`, `checksum`
- Replay engine: re-execute any workflow from its event log, compare output against stored traces, detect divergence
- Runtime uncertainty controls: confidence gating, 3-sample consistency check, critic pass for ambiguous signals
- Stale-state detection and agreement expiry handling
- Multi-provider LLM routing: Groq, Cerebras, Gemini — with retry, backoff, and deterministic fallback
- Redis Streams queue mode with DLQ for zero-loss async processing
- Escalation management with priority, SLA metadata, and operator handoff
- Channel routing with timezone enforcement, success rate tracking, and DNC hard gates
- Compliance guard: threat language, PII leakage, illegal promises — blocked before delivery
- Feedback collection and learning pipelines
- Adversarial evaluation harness for regression resistance

---

## API Surface

**Core workflow:**

- `POST /events` — ingest borrower event or system event
- `GET /workflows/{id}` — full workflow state with cost summary
- `GET /workflows/{id}/timeline` — event + decision history
- `GET /workflows/{id}/negotiation` — current negotiation state with behavioural signals
- `GET /workflows/{id}/messages` — outbound message log with compliance status
- `POST /workflows/{id}/replay` — re-execute from event log, return diff
- `GET /workflows/{id}/failures` — failure record for this workflow

**Operations:**

- `GET /escalations` — SLA-sorted escalation queue
- `POST /escalations/{id}/actions` — operator action (assign, resolve, close)
- `GET /economics/summary` — cost per workflow, per resolution, model breakdown
- `GET /metrics/business` — resolution rate, escalation rate, avg turns to close
- `GET /metrics` — infrastructure Prometheus metrics
- `POST /feedback` — operator signal capture
- `GET /failures/summary` — failure taxonomy and recovery rates
- `POST /incidents/simulate` — chaos testing
- `POST /learning/retraining/build` — generate retraining dataset from live traces
- `POST /learning/retraining/run` — run learning cycle
- `GET /trust/guarantees` — machine-readable trust contract

---

## Reliability

Collections systems fail in specific, predictable ways. Each one has a defined handling path:

- **Duplicate events** (UPI webhooks, gateway retries): `idempotency_key` deduplication. Same key = ignored.
- **LLM uncertainty**: 3-sample consistency check. `variance > 0.34` = intent degraded to UNKNOWN, workflow escalates.
- **LLM timeout or provider failure**: exponential retry across providers, deterministic fallback to rule-based extraction.
- **Invalid state transition**: `TransitionError` caught, workflow escalated, failure recorded.
- **Payment commitment expiry**: scheduler detects, emits timeout event, workflow re-engages borrower.
- **Borrower goes silent**: inactivity threshold configurable per segment; scheduler emits re-engagement event.
- **Tool failure** (payment link generation): saga compensation log records partial execution; operator can resolve.
- **Queue overflow or worker failure**: Redis Streams DLQ at `negotiation:events:dlq`. No silent discard.

---

## Evaluation and Safety

The test suite covers unit and integration paths. The adversarial evaluation harness covers cases that unit tests cannot — prompt injection, borrower contradiction, hardship-as-manipulation, deliberate ambiguity.

- Red-team adversarial cases for compliance violations and edge-case escalation paths
- Prompt-eval dataset helpers for replaying real traces offline with candidate prompt versions
- Experiment comparison helpers for measuring policy or prompt version changes against a baseline
- Retraining dataset generation from live decision traces
- Operator feedback capture for iteration signal

```bash
# Full test suite
uv run pytest -q

# Adversarial regression gate
uv run python scripts/regression_gate.py
```

---

## Running the System

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Docker (for Redis + containerized runtime)
- Node 18+ for the ops console

### Local backend

```bash
uv sync
uv run uvicorn api.app:app --reload
```

### Queue worker

```bash
uv run python scripts/run_worker.py
```

### Docker Compose

```bash
docker compose up --build
```

### Demo Data

Seed realistic borrower workflows with varied states — resolved, negotiating, escalated, awaiting payment, payment failed:

```bash
uv run python scripts/seed_demo_data.py
```

Each demo workflow includes behavioural signals, decision traces, and escalations. Safe to run multiple times.

---

## Configuration

```
DATABASE_URL            # PostgreSQL or SQLite connection string
REDIS_URL               # Redis connection for queue and DLQ
USE_QUEUE_INGEST        # true = async queue mode, false = direct processing
ORCHESTRATION_ENGINE    # custom (Temporal adapter boundary exists but is not active)
ENABLE_OTEL             # OpenTelemetry tracing

QUEUE_MAX_RETRIES               default: 3
QUEUE_RETRY_BACKOFF_SECONDS     default: 0.5

LLM_PROVIDER              groq | cerebras | gemini
LLM_REQUEST_TIMEOUT_SECONDS     default: 12
LLM_REQUEST_MAX_RETRIES         default: 3
GROQ_API_KEY / GROQ_MODEL
CEREBRAS_API_KEY / CEREBRAS_MODEL
GEMINI_API_KEY / GEMINI_MODEL
```

See `.env.example`.

---

## Learning Pipeline

Live decision traces are the training signal. The learning pipeline converts them into retraining data, runs evaluation against red-team scenarios, and measures prompt version performance against a baseline before any change ships.

```bash
uv run python scripts/build_retraining_dataset.py
uv run python scripts/run_learning_cycle.py
```

Artifacts written to `artifacts/retraining/latest/`.

---

## Current Scope

Implemented at production depth:

- Custom orchestrator with full state machine, policy, and compliance stack
- Multi-provider LLM extraction with consistency sampling and critic pass
- Behavioural intelligence: emotional state, behaviour pattern, dynamic strategy selection
- Redis Streams queue mode with DLQ and retry
- Ops console with workflow triage, escalation management, economics, feedback
- Feedback-driven learning pipeline and adversarial evaluation harness

Stubbed (real integrations are drop-in replacements):

- WhatsApp/SMS delivery — channel is string; replace with Twilio or Meta API
- Voice transcription — transcript field in payload; replace with STT
- Payment link — mock URL returned; replace with payment gateway
- Borrower CRM — deterministic profile loader; replace with API call to your CRM
- ML-based risk scoring — rule-based today; extend with model scores

Not implemented:

- Full Temporal SDK workflow/activity runtime (adapter boundary exists; Temporal fails fast if selected)
- Managed model retraining and serving automation

---

## Trust Guarantees

Machine-readable contract at `GET /trust/guarantees`.

- No duplicate action execution for the same `idempotency_key`
- Bounded failure paths: `retry → degrade → escalate` with stored taxonomy
- Replay and auditability: re-execute any workflow from its event log, detect divergence with SHA-256

Known assumptions:

- Database is the source of truth. State and traces are only as durable as the DB.
- Queue durability follows Redis stream and runtime configuration.

---

## Repository Layout

```
api/            FastAPI endpoints — event ingestion, queries, operations
workflow/       Orchestrator, state machine transitions, adapter boundary
agents/         LLM engine, policy engine, negotiation strategy, responder
infra/          Database, queue, scheduler, settings, observability
domain/         Core domain models, borrower profile, channel router, compliance
evals/          Red-team adversarial harness, prompt eval helpers
scripts/        Worker, learning cycle, seed data, regression gate
ops-console/    Next.js operator console
tests/          Unit, integration, and adversarial coverage
```

---

## Entry Points

If you are reading this as a technical evaluator, start here:

1. `workflow/orchestrator.py` — the execution engine; every design decision is visible here
2. `agents/policy_engine.py` — what the system actually decides and why
3. `agents/negotiation_strategy.py` — how the system handles a borrower in negotiation
4. `domain/models.py` — the data contracts that define system behaviour
5. `ops-console/` — what an operator sees when a workflow needs attention

---

Resolve AI is built to be operated, audited, and improved — not demoed once and shelved.

See `docs/architecture.md` for design decisions. See `docs/DEPLOYMENT.md` for production deployment.