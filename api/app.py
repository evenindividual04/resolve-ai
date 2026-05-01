from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
import logging
import json
import asyncio
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import text

from domain.models import EscalationAction, Event, FailureRecord, FeedbackSignal, IncidentSimulationRequest, IncidentSimulationResult, ReplayRequest
from infra.db import Database
from infra.observability import WORKFLOW_EVENTS, configure_logging, maybe_init_otel, metrics_response, tracing_middleware
from infra.queue import RedisEventQueue
from infra.scheduler import WorkflowScheduler
from infra.settings import settings
from workflow.factory import build_orchestration_adapter

db = Database(settings.database_url)
adapter = build_orchestration_adapter(db)
queue = RedisEventQueue(settings.redis_url)
scheduler = WorkflowScheduler(db, queue)


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    maybe_init_otel()
    await db.init()
    if settings.use_queue_ingest:
        await queue.ensure_group()
    scheduler_task = await scheduler.start()
    yield
    scheduler.stop()
    scheduler_task.cancel()


app = FastAPI(title="Autonomous Collections Intelligence Platform", version="0.2.0", lifespan=lifespan)
app.middleware("http")(tracing_middleware)
log = logging.getLogger(__name__)


@app.post("/events")
async def ingest_event(event: Event):
    if settings.use_queue_ingest:
        msg_id = await queue.publish(event)
        WORKFLOW_EVENTS.labels(status="queued").inc()
        return {"status": "queued", "message_id": msg_id, "workflow_id": event.workflow_id}
    out = await adapter.process_event(event)
    WORKFLOW_EVENTS.labels(status=str(out.get("status", "unknown"))).inc()
    log.info("event_processed workflow_id=%s status=%s", event.workflow_id, out.get("status"))
    return out


@app.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    row = await db.get_workflow(workflow_id)
    if not row:
        raise HTTPException(status_code=404, detail="workflow not found")

    traces = await db.list_traces(workflow_id)
    total_cost = round(sum(float(t["cost_usd"]) for t in traces), 6)
    total_tokens = sum(int(t["tokens_used"]) for t in traces)
    return {
        "workflow": row,
        "health": {
            "is_terminal": row["state"] in {"resolved", "escalated"},
            "last_updated": row["updated_at"],
        },
        "cost_summary": {
            "total_cost_usd": total_cost,
            "total_tokens": total_tokens,
            "cost_per_decision": round(total_cost / max(1, len(traces)), 6),
        },
    }


@app.get("/economics/summary")
async def economics_summary():
    async with db.engine.connect() as conn:
        rs = await conn.execute(text("SELECT cost_usd, tokens_used, workflow_id, model_name, final_action, is_llm_call FROM decision_traces"))
        trace_rows = [dict(r._mapping) for r in rs.fetchall()]
    total_cost = round(sum(float(r["cost_usd"]) for r in trace_rows), 6)
    total_tokens = sum(int(r["tokens_used"]) for r in trace_rows)
    workflows = {r["workflow_id"] for r in trace_rows}
    cost_per_workflow = round(total_cost / max(1, len(workflows)), 6)
    resolved = [r for r in trace_rows if r["final_action"] == "resolve"]
    failures = await db.list_failures()
    cost_per_resolution = round((sum(float(r["cost_usd"]) for r in resolved) / max(1, len(resolved))), 6)
    total_failure_cost = sum(float(f["cost_impact_usd"]) for f in failures)
    cost_per_failure = round(total_failure_cost / max(1, len(failures)), 6)
    model_breakdown: dict[str, float] = {}
    llm_call_breakdown: dict[str, int] = {"real": 0, "fallback": 0}
    for r in trace_rows:
        model_breakdown[r["model_name"]] = round(model_breakdown.get(r["model_name"], 0.0) + float(r["cost_usd"]), 6)
        if r.get("is_llm_call", 1):
            llm_call_breakdown["real"] += 1
        else:
            llm_call_breakdown["fallback"] += 1
    return {
        "total_cost_usd": total_cost,
        "total_tokens": total_tokens,
        "workflows_count": len(workflows),
        "cost_per_workflow": cost_per_workflow,
        "cost_per_resolution": cost_per_resolution,
        "cost_per_failure": cost_per_failure,
        "model_breakdown": model_breakdown,
        "llm_call_breakdown": llm_call_breakdown,
    }


@app.get("/workflows/{workflow_id}/trace")
async def get_trace(workflow_id: str):
    events = await db.list_events(workflow_id)
    traces = await db.list_traces(workflow_id)
    return {"events": events, "decisions": traces}


@app.get("/workflows/{workflow_id}/timeline")
async def get_timeline(workflow_id: str):
    return await get_trace(workflow_id)


@app.post("/workflows/{workflow_id}/replay")
async def replay_workflow(workflow_id: str, _: ReplayRequest):
    return await adapter.replay(workflow_id)


@app.get("/escalations")
async def list_escalations():
    rows = await db.list_escalations()
    now = datetime.now(UTC)
    out = []
    for r in rows:
        due = r["sla_due_at"]
        if due.tzinfo is None:
            due = due.replace(tzinfo=UTC)
        age_minutes = int((now - due).total_seconds() // 60)
        out.append({**r, "sla_breached": now > due, "sla_age_minutes": max(age_minutes, 0)})
    return out


@app.post("/feedback")
async def submit_feedback(signal: FeedbackSignal):
    await db.insert_feedback(
        {
            "workflow_id": signal.workflow_id,
            "decision_id": signal.decision_id,
            "signal_type": signal.signal_type,
            "rating": signal.rating,
            "notes": signal.notes,
            "created_at": datetime.now(UTC),
        }
    )
    return {"status": "ok"}


@app.get("/feedback")
async def list_feedback(workflow_id: str | None = None):
    rows = await db.list_feedback(workflow_id)
    return rows


@app.get("/workflows/{workflow_id}/failures")
async def workflow_failures(workflow_id: str):
    return await db.list_failures(workflow_id)


@app.get("/failures/summary")
async def failures_summary():
    failures = await db.list_failures()
    by_type: dict[str, int] = {}
    recovered = 0
    for f in failures:
        by_type[f["failure_type"]] = by_type.get(f["failure_type"], 0) + 1
        recovered += int(f["recovered"])
    return {
        "total": len(failures),
        "by_type": by_type,
        "recovery_success_rate": round(recovered / max(1, len(failures)), 4),
    }


@app.post("/incidents/simulate")
async def simulate_incident(req: IncidentSimulationRequest):
    incident_id = str(uuid4())
    recovery = "degraded"
    status = "simulated"
    details = {"payload": req.payload}
    if req.incident_type.value in {"llm_timeout", "tool_failure"}:
        recovery = "escalated"
        await db.insert_failure(
            {
                "workflow_id": req.workflow_id,
                "event_id": None,
                "failure_type": "infra_timeout_outage",
                "severity": "high",
                "recoverability": "medium",
                "recovery_strategy": "escalate",
                "recovered": 1,
                "cost_impact_usd": 0.0,
                "notes": f"incident:{req.incident_type.value}",
                "created_at": datetime.now(UTC),
            }
        )
    await db.insert_incident(
        {
            "incident_id": incident_id,
            "workflow_id": req.workflow_id,
            "incident_type": req.incident_type.value,
            "status": status,
            "recovery_status": recovery,
            "details": details,
            "created_at": datetime.now(UTC),
        }
    )
    return IncidentSimulationResult(
        incident_id=incident_id,
        workflow_id=req.workflow_id,
        incident_type=req.incident_type,
        status=status,
        recovery_status=recovery,
        details=details,
    )


@app.get("/incidents/{incident_id}")
async def get_incident(incident_id: str):
    row = await db.get_incident(incident_id)
    if not row:
        raise HTTPException(status_code=404, detail="incident not found")
    return dict(row)


@app.post("/learning/retraining/build")
async def build_retraining_dataset():
    proc = await asyncio.create_subprocess_exec(
        "python",
        "scripts/build_retraining_dataset.py",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=f"retraining_build_failed: {err.decode().strip()}")
    return json.loads(out.decode().strip())


@app.post("/learning/retraining/run")
async def run_learning_cycle():
    proc = await asyncio.create_subprocess_exec(
        "python",
        "scripts/run_learning_cycle.py",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=f"learning_cycle_failed: {err.decode().strip()}")
    return json.loads(out.decode().strip())


@app.post("/learning/self_critique/run")
async def self_critique_run():
    return {
        "status": "ok",
        "strategy": "primary_critic_refine",
        "hard_cap_passes": 2,
        "note": "runtime self-critique already enforced in orchestrator",
    }


@app.get("/trust/guarantees")
async def trust_guarantees():
    return {
        "guarantees": [
            "no duplicate actions under same idempotency_key",
            "bounded failure pathways: retry/degrade/escalate",
            "replay auditability with state diff",
        ],
        "known_limitations": [
            "temporal sdk implementation pending",
            "model retraining deployment automation is readiness-gated but manual",
        ],
        "assumptions": [
            "database availability for source-of-truth writes",
            "queue durability delegated to redis stream settings",
        ],
    }


@app.post("/escalations/{escalation_id}/action")
async def update_escalation(escalation_id: str, action: EscalationAction):
    row = await db.get_escalation(escalation_id)
    if not row:
        raise HTTPException(status_code=404, detail="escalation not found")
    row = dict(row)
    row["operator"] = action.operator
    row["status"] = action.status
    row["notes"] = action.notes
    await db.upsert_escalation(row)
    return {"status": "ok", "escalation_id": escalation_id}


@app.post("/escalations/{escalation_id}/actions")
async def update_escalation_plural(escalation_id: str, action: EscalationAction):
    return await update_escalation(escalation_id, action)


@app.get("/ops", response_class=HTMLResponse)
async def ops_panel() -> str:
    return """
    <html><head><title>Ops Panel</title>
    <style>
      body { font-family: 'IBM Plex Sans', sans-serif; background: linear-gradient(120deg,#f7f6f2,#ebeef9); padding: 24px; }
      .card { background:#fff; border:1px solid #ddd; border-radius:12px; padding:16px; margin-bottom:12px; }
      code { background:#f4f4f4; padding:2px 6px; border-radius:6px; }
    </style></head>
    <body>
      <h1>Durable Negotiation Ops</h1>
      <div class='card'>Use <code>POST /events</code> to ingest events with idempotency keys.</div>
      <div class='card'>Inspect traces: <code>GET /workflows/{id}/trace</code></div>
      <div class='card'>Escalations queue: <code>GET /escalations</code></div>
      <div class='card'>Replay digest: <code>POST /workflows/{id}/replay</code></div>
      <div class='card'>Metrics: <code>GET /metrics</code></div>
    </body></html>
    """


@app.get("/metrics")
async def metrics():
    return metrics_response()


@app.get("/metrics/business")
async def business_metrics():
    """Business-level KPIs for the collections platform.

    Unlike /metrics (infrastructure), this surfaces what actually matters:
    resolution rate, escalation rate, average turns to close, cost per
    resolved workflow, and compliance violations.
    """
    return await db.get_business_metrics()


@app.get("/workflows/{workflow_id}/messages")
async def workflow_messages(workflow_id: str):
    """Return all outbound messages generated for a workflow, with compliance status."""
    row = await db.get_workflow(workflow_id)
    if not row:
        raise HTTPException(status_code=404, detail="workflow not found")
    messages = await db.list_message_logs(workflow_id)
    return {"workflow_id": workflow_id, "messages": messages}


@app.get("/workflows/{workflow_id}/negotiation")
async def workflow_negotiation(workflow_id: str):
    """Return the current negotiation state: turn count, prior offers, counter-offer amount."""
    row = await db.get_workflow(workflow_id)
    if not row:
        raise HTTPException(status_code=404, detail="workflow not found")
    return {
        "workflow_id": workflow_id,
        "turn_count": row.get("turn_count", 0),
        "prior_offers": row.get("prior_offers") or [],
        "counter_offer_amount": row.get("counter_offer_amount"),
        "negotiated_amount": row.get("negotiated_amount"),
        "outstanding_amount": row.get("outstanding_amount"),
        "strike_count": row.get("strike_count", 0),
    }


@app.get("/workflows")
async def list_workflows(
    state: str | None = None,
    loan_segment: str | None = None,
    risk_band: str | None = None,
    limit: int = 200,
    offset: int = 0,
):
    """Paginated list of workflow summaries for the ops console workflow browser."""
    rows = await db.list_workflows(
        state=state,
        loan_segment=loan_segment,
        risk_band=risk_band,
        limit=limit,
        offset=offset,
    )
    return rows


@app.get("/borrowers")
async def list_borrowers(
    dnc_only: bool = False,
    risk_band: str | None = None,
    loan_segment: str | None = None,
    limit: int = 200,
    offset: int = 0,
):
    """Paginated list of borrower profiles for the ops console borrower intelligence page."""
    rows = await db.list_borrower_profiles(
        dnc_only=dnc_only,
        risk_band=risk_band,
        loan_segment=loan_segment,
        limit=limit,
        offset=offset,
    )
    return rows


@app.get("/borrowers/{user_id}")
async def get_borrower(user_id: str):
    """Return the borrower profile for a specific user_id."""
    row = await db.get_borrower_profile(user_id)
    if not row:
        raise HTTPException(status_code=404, detail="borrower profile not found")
    return row
