# Resolve AI
Resolve AI is an infra-first, production-grade AI workflow platform for high-stakes negotiation operations.

<p align="center">
  <video src="./video/out.mp4" controls width="100%" style="border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);"></video>
</p>

It is built for teams that need AI to act as a decision signal, not a free-form control plane. Every step is deterministic where it must be, traceable where it matters, and resilient when systems or models fail.

## Why It Exists
Most AI agent systems are easy to demo and hard to trust in production. Resolve AI is designed for the opposite:

- Predictable workflow execution under strict policy constraints
- Full auditability for every model decision, action, and retry
- Safe handling of ambiguity, abuse, stale state, and duplicate events
- A learning loop that turns real operator feedback into better prompts and better evaluation data

If you need to run AI over operational workflows where correctness, compliance, and reproducibility matter, this project is the control surface.

## What It Does
Resolve AI manages negotiation-style workflows end to end:

- Ingests events idempotently and records them as an append-only history
- Extracts structured intent from model outputs with provider routing and fallback behavior
- Applies deterministic policy gates before any action is allowed to move forward
- Maintains a decision ledger with costs, checksums, and replay data
- Escalates ambiguous or risky cases with SLA-aware operator workflows
- Exposes economics, incident, feedback, and learning endpoints for operational visibility
- Surfaces the entire system through an operator console built for fast triage

## Product Highlights
- Deterministic workflow state machine with strict transitions
- Decision traces that capture LLM output, policy output, costs, and replay checksums
- Replay engine for auditability and consistency verification
- Runtime uncertainty controls, including confidence gating and multi-run variance checks
- Stale-state detection and agreement expiry handling
- Multi-provider LLM routing across Groq, Cerebras, and Gemini
- Redis Streams queue mode for asynchronous execution
- Escalation management with priority and SLA metadata
- Observability endpoints for metrics, economics, failures, and trust guarantees
- Feedback collection and learning pipelines for continuous improvement
- Adversarial evaluation harness for regression resistance

## How It Works

### 1. Event Ingestion
Clients post workflow events to the API. Events are deduplicated via `idempotency_key`, persisted, and either processed immediately or queued for worker execution.

### 2. Structured Extraction
The LLM engine converts raw conversation text into structured intent output. If confidence is low or the decision looks risky, the system can run a verifier pass or fall back to deterministic extraction.

### 3. Policy Enforcement
Policy gates decide what is allowed, what should be clarified, and what must be escalated. This keeps model output from directly controlling the workflow.

### 4. Decision Ledger
Every execution writes a trace record with:

- input and output payloads
- prompt version and policy version
- model name
- confidence and cost
- checksum for replay validation
- autonomy level and failure annotations

### 5. Operator Review
Escalations, feedback, economics, and timeline views live in the ops console so non-engineers can inspect workflows without digging through raw logs.

### 6. Learning Loop
Feedback can be turned into retraining data and evaluated against red-team scenarios and real traces, making prompt iteration safer and more repeatable.

## Architecture

High-level runtime components:

- **API Layer (FastAPI):** event ingestion, workflow queries, replay, economics, feedback, incidents, and learning endpoints
- **Workflow Core:** deterministic orchestration and transition engine
- **Policy Engine:** compliance gates and action constraints
- **LLM Engine:** provider-routed extraction with retry and fallback logic
- **Storage:** PostgreSQL or SQLite for state and traces; Redis for queue transport
- **Ops Console (Next.js):** productized operator views for workflows, escalations, economics, feedback, incidents, and trace inspection

Execution modes:

- **Direct mode:** `POST /events` processes immediately in the API process
- **Queue mode:** `POST /events` enqueues to Redis Streams and a worker consumes the event

## Workflow Model

Primary states:

- `init`
- `contacted`
- `negotiating`
- `waiting_for_payment`
- `payment_failed`
- `resolved`
- `escalated`

Guarantees:

- Illegal transitions are blocked and escalated
- Duplicate events are safely deduplicated
- Replay can verify action sequence and resulting state

## API Surface

Core endpoints:

- `POST /events`
- `GET /workflows/{id}`
- `GET /workflows/{id}/timeline`
- `GET /workflows/{id}/trace` (legacy alias)
- `POST /workflows/{id}/replay`
- `GET /escalations`
- `POST /escalations/{id}/actions`
- `POST /escalations/{id}/action` (legacy alias)

Operations and governance:

- `GET /economics/summary`
- `GET /metrics`
- `POST /feedback`
- `GET /feedback`
- `GET /failures/summary`
- `GET /workflows/{id}/failures`
- `POST /incidents/simulate`
- `GET /incidents/{id}`
- `POST /learning/retraining/build`
- `POST /learning/retraining/run`
- `POST /learning/self_critique/run`
- `GET /trust/guarantees`

## Evaluation and Safety

The repository includes both regression-focused evaluation and learning infrastructure:

- red-team adversarial cases for prompt injection, contradiction, and hardship escalation
- prompt-eval dataset helpers for replaying real traces offline
- experiment comparison helpers for baseline vs candidate prompt versions
- retraining dataset generation and learning-cycle scripts
- operator feedback capture to improve future prompt and policy iterations

That combination is what makes the system practical for real teams: it is not only observable, it is measurable.

## LLM Providers

Supported providers:

- Groq
- Cerebras
- Gemini

Behavior:

- Structured JSON intent extraction
- Retry with exponential backoff
- Verifier pass for high-risk or low-confidence decisions
- Deterministic fallback when provider calls are unavailable or invalid

## Ops Console

Path: `ops-console/`

The console is designed as an internal product surface, not a bare dashboard.

Run it with:

```bash
cd ops-console
npm install
NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev
```

Available pages:

- `/` overview
- `/escalations`
- `/workflows/{id}`
- `/economics`
- `/feedback`
- `/incidents`

## Running the System

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Docker for containerized runtime
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

To populate the ops console with realistic sample workflows for immediate visibility:

```bash
# After services are up, seed demo workflows
uv run python scripts/seed_demo_data.py
```

This creates 5 sample workflows with events, decision traces, escalations, and feedback signals. The ops console dashboard will immediately show workflows in various states (resolved, negotiating, escalated, waiting for payment, payment failed).

Safe to run multiple times; uses idempotency to prevent duplicates.

## Configuration

Environment variables:

- `DATABASE_URL`
- `REDIS_URL`
- `USE_QUEUE_INGEST` (`true|false`)
- `ORCHESTRATION_ENGINE` (`custom`)
- `ENABLE_OTEL` (`true|false`)

Queue hardening:

- `QUEUE_MAX_RETRIES` (default: `3`)
- `QUEUE_RETRY_BACKOFF_SECONDS` (default: `0.5`)

LLM runtime hardening:

- `LLM_REQUEST_TIMEOUT_SECONDS` (default: `12`)
- `LLM_REQUEST_MAX_RETRIES` (default: `3`)
- `LLM_MIN_REQUEST_INTERVAL_SECONDS` (default: `0`)

LLM selection:

- `LLM_PROVIDER` (`groq|cerebras|gemini`)
- `GROQ_API_KEY`, `GROQ_MODEL`
- `CEREBRAS_API_KEY`, `CEREBRAS_MODEL`
- `GEMINI_API_KEY`, `GEMINI_MODEL`

See [.env.example](/Users/anmolsen/Developer/resolve-ai/.env.example).

## Testing and Quality Gates

Run the test suite:

```bash
uv run pytest -q
```

Run the adversarial evaluation gate:

```bash
uv run python scripts/regression_gate.py
```

Integration test path:

- PostgreSQL + Redis service containers
- Integration tests in `tests/test_integration_services.py`

## Learning Pipeline

Generate retraining artifacts:

```bash
uv run python scripts/build_retraining_dataset.py
```

Run the end-to-end learning cycle:

```bash
uv run python scripts/run_learning_cycle.py
```

Artifacts are written under `artifacts/retraining/` with a `latest/` mirror.

## Reliability and Safety Controls

- Idempotent event processing
- Guardrails for ambiguous, contradictory, or abusive input
- Escalation circuit paths with SLA metadata
- Replay validation for audit and consistency checks
- Structured operational metrics and trace IDs for incident triage

## Current Scope

Implemented:

- Custom orchestrator and adapter boundary
- Provider-routed LLM extraction
- Queue + worker model
- Operator-focused internal console
- Feedback-driven learning data pipeline
- Prompt-eval dataset and experiment helpers

Not implemented yet:

- Full Temporal SDK workflow/activity runtime, though the adapter boundary exists
- Fully managed model retraining and serving deployment automation
- Enterprise-grade alerting and dashboards beyond the current observability layer

Temporal is explicitly blocked in this build and will fail fast if selected.

## Trust Guarantees

Machine-readable trust contract is exposed at `GET /trust/guarantees`.

Current guarantees:

- No duplicate action execution for the same idempotency key
- Bounded failure paths (`retry`, `degrade`, `escalate`) with stored taxonomy
- Replay and auditability checks including state diff

Known assumptions:

- The database remains the source of truth for state and traces
- Queue durability follows Redis stream and runtime configuration

## Repository Layout

- `api/` FastAPI endpoints
- `workflow/` orchestration, transitions, adapters
- `agents/` LLM, policy, and tool actions
- `infra/` DB, queue, settings, observability
- `domain/` contracts and channel normalization
- `evals/` red-team and evaluation harness
- `scripts/` worker and learning utilities
- `ops-console/` Next.js operator console
- `tests/` unit, integration, and regression tests

## Suggested Entry Points

If you are evaluating this project as a product, start here:

1. `workflow/orchestrator.py` for execution semantics
2. `api/app.py` for the public contract and runtime mode
3. `ops-console/` for the operator experience
4. `tests/` for reliability and adversarial coverage

---

Resolve AI is meant to be operated, audited, and improved, not just demoed.

See `docs/DEPLOYMENT.md` for a production deployment runbook without Temporal.