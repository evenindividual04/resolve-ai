from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
import json

from sqlalchemy import JSON, Column, DateTime, Float, Integer, MetaData, String, Table, Text, insert, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

metadata = MetaData()

workflows = Table(
    "workflows",
    metadata,
    Column("workflow_id", String, primary_key=True),
    Column("user_id", String, nullable=False),
    Column("state", String, nullable=False),
    Column("outstanding_amount", Float, nullable=False),
    Column("negotiated_amount", Float, nullable=True),
    Column("strike_count", Integer, nullable=False),
    Column("last_message", Text, nullable=False),
    Column("history_summary", Text, nullable=False),
    Column("version", Integer, nullable=False),
    Column("prompt_version", String, nullable=False),
    Column("policy_version", String, nullable=False),
    Column("context_version", String, nullable=False, default="ctx_v1"),
    Column("autonomy_level", String, nullable=False, default="human_review"),
    Column("stale_after_hours", Integer, nullable=False, default=48),
    Column("last_revalidated_at", DateTime(timezone=True), nullable=True),
    Column("agreement_expires_at", DateTime(timezone=True), nullable=True),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

events = Table(
    "events",
    metadata,
    Column("event_id", String, primary_key=True),
    Column("workflow_id", String, nullable=False),
    Column("event_type", String, nullable=False),
    Column("channel", String, nullable=False),
    Column("payload", JSON, nullable=False),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("idempotency_key", String, nullable=False, unique=True),
    Column("schema_version", String, nullable=False),
)

decision_traces = Table(
    "decision_traces",
    metadata,
    Column("decision_id", String, primary_key=True),
    Column("workflow_id", String, nullable=False),
    Column("event_id", String, nullable=False),
    Column("llm_output", JSON, nullable=False),
    Column("policy_result", JSON, nullable=False),
    Column("final_action", String, nullable=False),
    Column("prompt_version", String, nullable=False),
    Column("policy_version", String, nullable=False),
    Column("model_name", String, nullable=False),
    Column("confidence", Float, nullable=False),
    Column("tokens_used", Integer, nullable=False),
    Column("cost_usd", Float, nullable=False),
    Column("checksum", String, nullable=False),
    Column("autonomy_level", String, nullable=False, default="human_review"),
    Column("critic_result", JSON, nullable=False, default={}),
    Column("consistency_variance", Float, nullable=False, default=0.0),
    Column("failure_score", JSON, nullable=False, default={}),
    Column("tool_compensation_applied", Integer, nullable=False, default=0),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

escalations = Table(
    "escalations",
    metadata,
    Column("escalation_id", String, primary_key=True),
    Column("workflow_id", String, nullable=False),
    Column("reason", String, nullable=False),
    Column("priority", Integer, nullable=False),
    Column("sla_due_at", DateTime(timezone=True), nullable=False),
    Column("status", String, nullable=False),
    Column("operator", String, nullable=True),
    Column("notes", Text, nullable=False),
)

feedback_signals = Table(
    "feedback_signals",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("workflow_id", String, nullable=False),
    Column("decision_id", String, nullable=True),
    Column("signal_type", String, nullable=False),
    Column("rating", Integer, nullable=False),
    Column("notes", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

failure_records = Table(
    "failure_records",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("workflow_id", String, nullable=False),
    Column("event_id", String, nullable=True),
    Column("failure_type", String, nullable=False),
    Column("severity", String, nullable=False),
    Column("recoverability", String, nullable=False),
    Column("recovery_strategy", String, nullable=False),
    Column("recovered", Integer, nullable=False, default=0),
    Column("cost_impact_usd", Float, nullable=False, default=0.0),
    Column("notes", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

incident_runs = Table(
    "incident_runs",
    metadata,
    Column("incident_id", String, primary_key=True),
    Column("workflow_id", String, nullable=False),
    Column("incident_type", String, nullable=False),
    Column("status", String, nullable=False),
    Column("recovery_status", String, nullable=False),
    Column("details", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

tool_executions = Table(
    "tool_executions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("workflow_id", String, nullable=False),
    Column("tool_name", String, nullable=False),
    Column("status", String, nullable=False),
    Column("payload", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)


class Database:
    def __init__(self, url: str = "sqlite+aiosqlite:///./agent.db") -> None:
        self.engine: AsyncEngine = create_async_engine(url, future=True)

    async def init(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(metadata.create_all)
            # Lightweight in-place compatibility migrations for existing SQLite dev DBs.
            for stmt in [
                "ALTER TABLE workflows ADD COLUMN context_version VARCHAR DEFAULT 'ctx_v1'",
                "ALTER TABLE workflows ADD COLUMN autonomy_level VARCHAR DEFAULT 'human_review'",
                "ALTER TABLE workflows ADD COLUMN stale_after_hours INTEGER DEFAULT 48",
                "ALTER TABLE workflows ADD COLUMN last_revalidated_at TIMESTAMP NULL",
                "ALTER TABLE workflows ADD COLUMN agreement_expires_at TIMESTAMP NULL",
                "ALTER TABLE decision_traces ADD COLUMN autonomy_level VARCHAR DEFAULT 'human_review'",
                "ALTER TABLE decision_traces ADD COLUMN critic_result JSON DEFAULT '{}'",
                "ALTER TABLE decision_traces ADD COLUMN consistency_variance FLOAT DEFAULT 0.0",
                "ALTER TABLE decision_traces ADD COLUMN failure_score JSON DEFAULT '{}'",
                "ALTER TABLE decision_traces ADD COLUMN tool_compensation_applied INTEGER DEFAULT 0",
            ]:
                try:
                    await conn.exec_driver_sql(stmt)
                except Exception:
                    pass

    async def upsert_workflow(self, row: dict) -> None:
        async with self.engine.begin() as conn:
            current = (await conn.execute(select(workflows).where(workflows.c.workflow_id == row["workflow_id"]))).first()
            if current is None:
                await conn.execute(insert(workflows).values(**row))
            else:
                await conn.execute(update(workflows).where(workflows.c.workflow_id == row["workflow_id"]).values(**row))

    async def get_workflow(self, workflow_id: str):
        async with self.engine.connect() as conn:
            return (await conn.execute(select(workflows).where(workflows.c.workflow_id == workflow_id))).mappings().first()

    async def insert_event(self, row: dict) -> bool:
        async with self.engine.begin() as conn:
            dup = (await conn.execute(select(events.c.event_id).where(events.c.idempotency_key == row["idempotency_key"]))).first()
            if dup:
                return False
            await conn.execute(insert(events).values(**row))
            return True

    async def list_events(self, workflow_id: str):
        async with self.engine.connect() as conn:
            rs = await conn.execute(select(events).where(events.c.workflow_id == workflow_id).order_by(events.c.occurred_at.asc()))
            return [r._mapping for r in rs.fetchall()]

    async def insert_trace(self, row: dict) -> None:
        async with self.engine.begin() as conn:
            await conn.execute(insert(decision_traces).values(**row))

    async def list_traces(self, workflow_id: str):
        async with self.engine.connect() as conn:
            rs = await conn.execute(select(decision_traces).where(decision_traces.c.workflow_id == workflow_id).order_by(decision_traces.c.created_at.asc()))
            return [r._mapping for r in rs.fetchall()]

    async def list_all_traces(self):
        async with self.engine.connect() as conn:
            rs = await conn.execute(select(decision_traces).order_by(decision_traces.c.created_at.asc()))
            return [r._mapping for r in rs.fetchall()]

    async def upsert_escalation(self, row: dict) -> None:
        async with self.engine.begin() as conn:
            current = (await conn.execute(select(escalations).where(escalations.c.escalation_id == row["escalation_id"]))).first()
            if current is None:
                await conn.execute(insert(escalations).values(**row))
            else:
                await conn.execute(update(escalations).where(escalations.c.escalation_id == row["escalation_id"]).values(**row))

    async def list_escalations(self):
        async with self.engine.connect() as conn:
            rs = await conn.execute(select(escalations).order_by(escalations.c.priority.asc(), escalations.c.sla_due_at.asc()))
            return [r._mapping for r in rs.fetchall()]

    async def get_escalation(self, escalation_id: str):
        async with self.engine.connect() as conn:
            return (await conn.execute(select(escalations).where(escalations.c.escalation_id == escalation_id))).mappings().first()

    async def insert_feedback(self, row: dict) -> None:
        async with self.engine.begin() as conn:
            await conn.execute(insert(feedback_signals).values(**row))

    async def list_feedback(self, workflow_id: str | None = None):
        async with self.engine.connect() as conn:
            q = select(feedback_signals).order_by(feedback_signals.c.created_at.desc())
            if workflow_id:
                q = q.where(feedback_signals.c.workflow_id == workflow_id)
            rs = await conn.execute(q)
            return [r._mapping for r in rs.fetchall()]

    async def insert_failure(self, row: dict) -> None:
        async with self.engine.begin() as conn:
            await conn.execute(insert(failure_records).values(**row))

    async def list_failures(self, workflow_id: str | None = None):
        async with self.engine.connect() as conn:
            q = select(failure_records).order_by(failure_records.c.created_at.desc())
            if workflow_id:
                q = q.where(failure_records.c.workflow_id == workflow_id)
            rs = await conn.execute(q)
            return [r._mapping for r in rs.fetchall()]

    async def insert_incident(self, row: dict) -> None:
        async with self.engine.begin() as conn:
            await conn.execute(insert(incident_runs).values(**row))

    async def get_incident(self, incident_id: str):
        async with self.engine.connect() as conn:
            return (await conn.execute(select(incident_runs).where(incident_runs.c.incident_id == incident_id))).mappings().first()

    async def insert_tool_execution(self, row: dict) -> None:
        async with self.engine.begin() as conn:
            await conn.execute(insert(tool_executions).values(**row))

    async def list_tool_executions(self, workflow_id: str):
        async with self.engine.connect() as conn:
            rs = await conn.execute(select(tool_executions).where(tool_executions.c.workflow_id == workflow_id).order_by(tool_executions.c.created_at.asc()))
            return [r._mapping for r in rs.fetchall()]
