# Durable Negotiation Agent
A production-oriented AI workflow system for financial negotiation operations.

The system treats AI as a **signal producer**, not a control plane. Workflow execution is deterministic, stateful, auditable, and resilient to partial failures.

## Product Overview
This platform is designed for high-stakes collections/repayment negotiation where correctness, compliance, and reproducibility matter more than raw model creativity.

Core principles:
- Non-deterministic model outputs are gated by deterministic policy and workflow transitions.
- Every decision is traceable, replayable, and cost-attributed.
- Failure handling (duplicate events, infra issues, ambiguity, abuse) is part of normal operation.

## Key Capabilities
- Deterministic workflow state machine with strict transition rules.
- Idempotent event ingestion (`idempotency_key`) and append-only event history.
- Decision trace ledger per step (LLM output, policy output, final action, checksums, costs).
- Replay engine with action-sequence and state-consistency checks.
- Policy and guardrails (confidence gating, contradiction checks, abuse/hardship routing).
- Runtime uncertainty controls: autonomy levels, self-critique/refine loop, multi-run consistency variance gate.
- Temporal consistency controls: stale-state detection, agreement expiry, revalidation path.
- Multi-provider LLM routing (`groq`, `cerebras`, `gemini`) with fallback behavior.
- Redis Streams queue mode with background worker processing.
- Escalation management with priority/SLA metadata and operator actions.
- Economics and observability endpoints (`/economics/summary`, `/metrics`).
- Learning loop via feedback capture + automated retraining dataset pipeline.
- Incident simulation mode and failure taxonomy tracking with recovery outcomes.

## Architecture
High-level runtime components:
- **API Layer (FastAPI):** ingestion, workflow queries, replay, escalations, economics, feedback.
- **Workflow Core:** deterministic orchestration logic + transition engine.
- **Policy Engine:** compliance gates and action constraints.
- **LLM Engine:** provider-routed structured extraction + verifier fallback.
- **Storage:** PostgreSQL/SQLite for system-of-record state; Redis for queue transport.
- **Ops Console (Next.js):** operator-focused views for workflows, escalations, economics, feedback.

Execution modes:
- **Direct mode:** `POST /events` processes immediately in API process.
- **Queue mode:** `POST /events` enqueues to Redis Streams; worker consumes and executes.

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
- Illegal transitions are blocked and escalated.
- Duplicate events are safely deduplicated.
- Replay can verify consistency of action sequence and resulting state.

## API Surface
Core endpoints:
- `POST /events`
- `GET /workflows/{id}`
- `GET /workflows/{id}/timeline` (primary)
- `GET /workflows/{id}/trace` (legacy alias)
- `POST /workflows/{id}/replay`
- `GET /escalations`
- `POST /escalations/{id}/actions` (primary)
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

## LLM Providers
Supported providers:
- Groq
- Cerebras
- Gemini

Behavior:
- Structured JSON intent extraction.
- Retry with exponential backoff.
- Verifier pass for high-risk/low-confidence decisions.
- Deterministic local fallback when provider call is unavailable or invalid.

## Running the System
### Prerequisites
- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Docker (for containerized runtime)
- Node 18+ (for ops console)

### Local backend
```bash
uv sync
uv run uvicorn api.app:app --reload
```

### Queue worker
```bash
uv run python scripts/run_worker.py
```

### Docker Compose (app + worker + postgres + redis)
```bash
docker compose up --build
```

## Configuration
Environment variables:
- `DATABASE_URL`
- `REDIS_URL`
- `USE_QUEUE_INGEST` (`true|false`)
- `ORCHESTRATION_ENGINE` (`custom|temporal`)
- `ENABLE_OTEL` (`true|false`)

LLM selection:
- `LLM_PROVIDER` (`groq|cerebras|gemini`)
- `GROQ_API_KEY`, `GROQ_MODEL`
- `CEREBRAS_API_KEY`, `CEREBRAS_MODEL`
- `GEMINI_API_KEY`, `GEMINI_MODEL`

See [.env.example](/Users/anmolsen/Developer/resolve-ai/.env.example).

## Ops Console
Path: `ops-console/`

Run:
```bash
cd ops-console
npm install
NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev
```

Pages:
- `/` overview
- `/escalations`
- `/workflows/{id}`
- `/economics`
- `/feedback`
- `/incidents`

## Testing & Quality Gates
Run tests:
```bash
uv run pytest -q
```

Run adversarial gate:
```bash
uv run python scripts/regression_gate.py
```

Integration test path (CI services):
- PostgreSQL + Redis service containers
- Integration tests in `tests/test_integration_services.py`

## Learning Pipeline
Generate retraining artifacts:
```bash
uv run python scripts/build_retraining_dataset.py
```

Run end-to-end learning cycle:
```bash
uv run python scripts/run_learning_cycle.py
```

Artifacts are written under `artifacts/retraining/` with a `latest/` mirror.

## Reliability and Safety Controls
- Idempotent event processing.
- Guardrails for ambiguous/contradictory/abusive input.
- Escalation circuit paths with SLA metadata.
- Replay validation for audit and consistency checks.
- Structured operational metrics and trace IDs for incident triage.

## Current Scope and Boundaries
Implemented:
- Custom orchestrator and adapter boundary.
- Provider-routed LLM extraction.
- Queue + worker model.
- Operator-focused internal console.
- Feedback-driven learning data pipeline.

Not implemented yet:
- Full Temporal SDK workflow/activity runtime (adapter exists).
- Full managed model retraining/serving deployment automation.
- Full enterprise observability dashboards/alert policies.

## Trust Guarantees
Machine-readable trust contract is exposed at `GET /trust/guarantees`.

Current guarantees:
- No duplicate action execution for the same idempotency key.
- Bounded failure paths (`retry`, `degrade`, `escalate`) with stored taxonomy.
- Replay/auditability checks including state diff.

Known assumptions:
- Database remains the source of truth for state and traces.
- Queue durability follows Redis stream/runtime configuration.

## 3-Month Ownership Roadmap
- Temporal SDK workflow/activity integration behind the existing adapter boundary.
- Real payment gateway hardening with signed webhooks and reconciliation.
- Voice channel productionization (streaming ingest + ASR confidence controls).
- Policy-learning loop evolution: data readiness -> managed fine-tune job -> controlled rollout.

## Repository Layout
- `api/` FastAPI endpoints
- `workflow/` orchestration, transitions, adapters
- `agents/` LLM + policy + tool actions
- `infra/` DB, queue, settings, observability
- `domain/` contracts and channel normalization
- `evals/` red-team and evaluation harness
- `scripts/` worker + learning/retraining utilities
- `ops-console/` Next.js operator console
- `tests/` unit/integration/regression tests

---
If you are evaluating this project for production readiness, start with:
1. `workflow/orchestrator.py` (execution semantics)
2. `api/app.py` (public contract and runtime mode)
3. `tests/` (reliability and adversarial coverage)
