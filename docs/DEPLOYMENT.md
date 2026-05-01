# Production Deployment (Without Temporal)

This project is production-ready on the custom orchestrator path.

`ORCHESTRATION_ENGINE` must be set to `custom`.

## 1. Required Services

- PostgreSQL 16+
- Redis 7+
- One API deployment (`api.app`)
- One or more worker deployments (`scripts/run_worker.py`)

## 2. Required Environment Variables

- `DATABASE_URL`
- `REDIS_URL`
- `ORCHESTRATION_ENGINE=custom`
- `LLM_PROVIDER` and provider-specific credentials

## 3. Recommended Runtime Defaults

Queue resilience:

- `QUEUE_MAX_RETRIES=3`
- `QUEUE_RETRY_BACKOFF_SECONDS=0.5`

LLM resilience:

- `LLM_REQUEST_TIMEOUT_SECONDS=12`
- `LLM_REQUEST_MAX_RETRIES=3`
- `LLM_MIN_REQUEST_INTERVAL_SECONDS=0`

## 4. Rollout Sequence

1. Deploy PostgreSQL and Redis.
2. Apply API deployment with `USE_QUEUE_INGEST=true`.
3. Deploy workers with the same `DATABASE_URL`, `REDIS_URL`, and LLM settings.
4. Verify health by sending a test event to `POST /events` and confirming:
   - queued response in API
   - workflow progression in `GET /workflows/{id}`
   - trace rows in `GET /workflows/{id}/trace`

## 5. Failure Behavior

- Worker retries failed events with incremental backoff.
- Events that exceed retry budget are moved to dead-letter stream `negotiation:events:dlq`.
- Original failed queue messages are acknowledged after requeue or dead-letter publish.

## 6. Quick Demo Setup

To populate the dashboard with realistic sample data for immediate visibility:

```bash
# Initialize database schema
export DATABASE_URL="postgresql://user:pass@localhost/negotiate"
export REDIS_URL="redis://localhost:6379"

# Seed demo workflows (5 workflows with events, traces, escalations)
python scripts/seed_demo_data.py
```

This creates:
- 5 sample workflows (resolved, negotiating, escalated, waiting, payment_failed)
- 6 events with realistic conversation histories
- 5 decision traces with real cost and token data
- 2 escalations for manual review
- 2 feedback signals
- 1 failure record

Safe to run multiple times; uses idempotency to avoid duplicates.

## 7. Temporal Status

Temporal execution is explicitly unsupported in this build and fails fast by design.

To avoid boot failures, do not set `ORCHESTRATION_ENGINE=temporal`.