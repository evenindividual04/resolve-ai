from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
import json

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, MetaData, String, Table, Text, insert, select, update, text
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
    Column("counter_offer_amount", Float, nullable=True),
    Column("strike_count", Integer, nullable=False),
    Column("turn_count", Integer, nullable=False, default=0),
    Column("prior_offers", JSON, nullable=True, default=[]),
    Column("loan_segment", String, nullable=True, default="personal"),
    Column("risk_band", String, nullable=True, default="medium"),
    Column("last_message", Text, nullable=False),
    Column("history_summary", Text, nullable=False),
    Column("version", Integer, nullable=False),
    Column("prompt_version", String, nullable=False),
    Column("policy_version", String, nullable=False),
    Column("context_version", String, nullable=False, default="ctx_v1"),
    Column("autonomy_level", String, nullable=False, default="human_review"),
    Column("stale_after_hours", Integer, nullable=False, default=48),
    Column("emotional_state", String, nullable=False, default="neutral"),
    Column("behavior_pattern", String, nullable=False, default="compliant"),
    Column("active_strategy", String, nullable=False, default="pragmatic"),
    Column("channel_metrics", JSON, nullable=False, default={}),
    Column("next_contact_scheduled_at", DateTime(timezone=True), nullable=True),
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
    Column("is_llm_call", Integer, nullable=False, default=1),
    Column("autonomy_level", String, nullable=False, default="full_auto"),
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

message_logs = Table(
    "message_logs",
    metadata,
    Column("message_id", String, primary_key=True),
    Column("workflow_id", String, nullable=False),
    Column("channel", String, nullable=False),
    Column("direction", String, nullable=False, default="outbound"),
    Column("content", Text, nullable=False),
    Column("action", String, nullable=False),
    Column("compliance_passed", Integer, nullable=False, default=1),
    Column("violations", JSON, nullable=False, default=[]),
    Column("sent_at", DateTime(timezone=True), nullable=False),
    Column("delivered_at", DateTime(timezone=True), nullable=True),
    Column("read_at", DateTime(timezone=True), nullable=True),
)

borrower_profiles = Table(
    "borrower_profiles",
    metadata,
    Column("user_id", String, primary_key=True),
    Column("risk_band", String, nullable=False, default="medium"),
    Column("loan_segment", String, nullable=False, default="personal"),
    Column("outstanding_amount", Float, nullable=False, default=0.0),
    Column("dpd", Integer, nullable=False, default=0),
    Column("prior_defaults", Integer, nullable=False, default=0),
    Column("contact_attempts", Integer, nullable=False, default=0),
    Column("preferred_channel", String, nullable=False, default="sms"),
    Column("language", String, nullable=False, default="en"),
    Column("timezone", String, nullable=False, default="Asia/Kolkata"),
    Column("dnc_flag", Integer, nullable=False, default=0),
    Column("legal_flag", Integer, nullable=False, default=0),
    Column("notes", Text, nullable=False, default=""),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)


class Database:
    def __init__(self, url: str = "sqlite+aiosqlite:///./agent.db") -> None:
        self.engine: AsyncEngine = create_async_engine(url, future=True)

    async def init(self) -> None:
        async with self.engine.begin() as conn:
            await conn.run_sync(metadata.create_all)
            # Lightweight in-place compatibility migrations for existing SQLite dev DBs.
            if self.engine.dialect.name == "sqlite":
                for stmt in [
                    "ALTER TABLE workflows ADD COLUMN context_version VARCHAR DEFAULT 'ctx_v1'",
                    "ALTER TABLE workflows ADD COLUMN autonomy_level VARCHAR DEFAULT 'human_review'",
                    "ALTER TABLE workflows ADD COLUMN stale_after_hours INTEGER DEFAULT 48",
                    "ALTER TABLE workflows ADD COLUMN last_revalidated_at TIMESTAMP NULL",
                    "ALTER TABLE workflows ADD COLUMN agreement_expires_at TIMESTAMP NULL",
                    "ALTER TABLE workflows ADD COLUMN counter_offer_amount FLOAT NULL",
                    "ALTER TABLE workflows ADD COLUMN turn_count INTEGER DEFAULT 0",
                    "ALTER TABLE workflows ADD COLUMN prior_offers JSON DEFAULT '[]'",
                    "ALTER TABLE workflows ADD COLUMN loan_segment VARCHAR DEFAULT 'personal'",
                    "ALTER TABLE workflows ADD COLUMN risk_band VARCHAR DEFAULT 'medium'",
                    "ALTER TABLE workflows ADD COLUMN emotional_state VARCHAR DEFAULT 'neutral'",
                    "ALTER TABLE workflows ADD COLUMN behavior_pattern VARCHAR DEFAULT 'compliant'",
                    "ALTER TABLE workflows ADD COLUMN active_strategy VARCHAR DEFAULT 'pragmatic'",
                    "ALTER TABLE workflows ADD COLUMN channel_metrics JSON DEFAULT '{}'",
                    "ALTER TABLE workflows ADD COLUMN next_contact_scheduled_at TIMESTAMP NULL",
                    "ALTER TABLE decision_traces ADD COLUMN autonomy_level VARCHAR DEFAULT 'human_review'",
                    "ALTER TABLE decision_traces ADD COLUMN critic_result JSON DEFAULT '{}'",
                    "ALTER TABLE decision_traces ADD COLUMN consistency_variance FLOAT DEFAULT 0.0",
                    "ALTER TABLE decision_traces ADD COLUMN failure_score JSON DEFAULT '{}'",
                    "ALTER TABLE decision_traces ADD COLUMN tool_compensation_applied INTEGER DEFAULT 0",
                    "ALTER TABLE decision_traces ADD COLUMN is_llm_call INTEGER DEFAULT 1",
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

    async def list_all_events(self):
        async with self.engine.connect() as conn:
            rs = await conn.execute(select(events).order_by(events.c.occurred_at.asc()))
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

    async def list_prompt_eval_rows(self, *, workflow_id: str | None = None, prompt_version: str | None = None):
        events_rows = await self.list_events(workflow_id) if workflow_id else await self.list_all_events()
        traces_rows = await self.list_all_traces()
        event_by_id = {str(row["event_id"]): dict(row) for row in events_rows}
        rows: list[dict] = []
        for trace in traces_rows:
            if prompt_version and trace["prompt_version"] != prompt_version:
                continue
            event = event_by_id.get(str(trace["event_id"]))
            if event is None:
                continue
            rows.append({"event": event, "trace": dict(trace)})
        return rows

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

    async def insert_message_log(self, row: dict) -> None:
        async with self.engine.begin() as conn:
            await conn.execute(insert(message_logs).values(**row))

    async def list_message_logs(self, workflow_id: str):
        async with self.engine.connect() as conn:
            rs = await conn.execute(
                select(message_logs)
                .where(message_logs.c.workflow_id == workflow_id)
                .order_by(message_logs.c.sent_at.asc())
            )
            return [dict(r._mapping) for r in rs.fetchall()]

    async def upsert_borrower_profile(self, row: dict) -> None:
        async with self.engine.begin() as conn:
            current = (await conn.execute(
                select(borrower_profiles).where(borrower_profiles.c.user_id == row["user_id"])
            )).first()
            if current is None:
                await conn.execute(insert(borrower_profiles).values(**row))
            else:
                await conn.execute(
                    update(borrower_profiles)
                    .where(borrower_profiles.c.user_id == row["user_id"])
                    .values(**row)
                )

    async def get_borrower_profile(self, user_id: str):
        async with self.engine.connect() as conn:
            return (await conn.execute(
                select(borrower_profiles).where(borrower_profiles.c.user_id == user_id)
            )).mappings().first()

    async def list_workflows_pending_timeout(self, now_iso: str) -> list[dict]:
        """Return workflows in WAITING_FOR_PAYMENT with expired agreement windows."""
        from sqlalchemy import text
        async with self.engine.connect() as conn:
            rs = await conn.execute(text(
                "SELECT workflow_id, user_id, agreement_expires_at "
                "FROM workflows "
                "WHERE state = 'waiting_for_payment' "
                "AND agreement_expires_at IS NOT NULL "
                "AND agreement_expires_at < :now"
            ), {"now": now_iso})
            return [dict(r._mapping) for r in rs.fetchall()]

    async def list_stale_negotiating_workflows(self, cutoff_iso: str) -> list[dict]:
        """Return NEGOTIATING workflows that haven't been updated since the cutoff."""
        from sqlalchemy import text
        async with self.engine.connect() as conn:
            rs = await conn.execute(text(
                "SELECT workflow_id, user_id, updated_at, stale_after_hours "
                "FROM workflows "
                "WHERE state = 'negotiating' "
                "AND updated_at < :cutoff"
            ), {"cutoff": cutoff_iso})
            return [dict(r._mapping) for r in rs.fetchall()]

    async def get_business_metrics(self) -> dict:
        """Compute business-level metrics for the /metrics/business endpoint."""
        from sqlalchemy import text
        async with self.engine.connect() as conn:
            total_rs = await conn.execute(text("SELECT COUNT(*) as cnt FROM workflows"))
            total_workflows = total_rs.fetchone()[0]

            resolved_rs = await conn.execute(text("SELECT COUNT(*) as cnt FROM workflows WHERE state = 'resolved'"))
            resolved = resolved_rs.fetchone()[0]

            escalated_rs = await conn.execute(text("SELECT COUNT(*) as cnt FROM workflows WHERE state = 'escalated'"))
            escalated = escalated_rs.fetchone()[0]

            halted_rs = await conn.execute(text("SELECT COUNT(*) as cnt FROM workflows WHERE state = 'halted'"))
            halted = halted_rs.fetchone()[0]

            turns_rs = await conn.execute(text(
                "SELECT AVG(turn_count) as avg_turns FROM workflows WHERE state IN ('resolved', 'escalated')"
            ))
            avg_turns = turns_rs.fetchone()[0] or 0.0

            cost_rs = await conn.execute(text(
                "SELECT SUM(cost_usd) as total, COUNT(*) as cnt FROM decision_traces"
            ))
            cost_row = cost_rs.fetchone()
            total_cost = cost_row[0] or 0.0
            total_decisions = cost_row[1] or 0

            cost_per_resolved = 0.0
            if resolved > 0:
                res_cost_rs = await conn.execute(text(
                    "SELECT SUM(dt.cost_usd) FROM decision_traces dt "
                    "JOIN workflows w ON dt.workflow_id = w.workflow_id "
                    "WHERE w.state = 'resolved'"
                ))
                cost_per_resolved = round((res_cost_rs.fetchone()[0] or 0.0) / resolved, 6)

            compliance_rs = await conn.execute(text(
                "SELECT COUNT(*) as cnt FROM message_logs WHERE compliance_passed = 0"
            ))
            compliance_violations = compliance_rs.fetchone()[0]

        return {
            "total_workflows": total_workflows,
            "resolved": resolved,
            "escalated": escalated,
            "halted": halted,
            "resolution_rate": round(resolved / max(1, total_workflows), 4),
            "escalation_rate": round(escalated / max(1, total_workflows), 4),
            "avg_turns_to_close": round(float(avg_turns), 2),
            "total_cost_usd": round(float(total_cost), 6),
            "cost_per_resolved_workflow": cost_per_resolved,
            "compliance_violations": compliance_violations,
            "total_decisions": total_decisions,
        }

    async def list_workflows(
        self,
        state: str | None = None,
        loan_segment: str | None = None,
        risk_band: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict]:
        """Return a paginated list of workflow summary rows for the ops console browser."""
        conditions = []
        params: dict = {"limit": limit, "offset": offset}

        if state:
            conditions.append("state = :state")
            params["state"] = state
        if loan_segment:
            conditions.append("loan_segment = :loan_segment")
            params["loan_segment"] = loan_segment
        if risk_band:
            conditions.append("risk_band = :risk_band")
            params["risk_band"] = risk_band

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = text(
            f"SELECT workflow_id, user_id, state, outstanding_amount, negotiated_amount, "
            f"turn_count, strike_count, loan_segment, risk_band, updated_at "
            f"FROM workflows {where} "
            f"ORDER BY updated_at DESC LIMIT :limit OFFSET :offset"
        )

        async with self.engine.connect() as conn:
            rs = await conn.execute(sql, params)
            return [dict(row._mapping) for row in rs.fetchall()]

    async def list_borrower_profiles(
        self,
        dnc_only: bool = False,
        risk_band: str | None = None,
        loan_segment: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict]:
        """Return a paginated list of borrower profiles for the ops console."""
        conditions = []
        params: dict = {"limit": limit, "offset": offset}

        if dnc_only:
            conditions.append("dnc_flag = 1")
        if risk_band:
            conditions.append("risk_band = :risk_band")
            params["risk_band"] = risk_band
        if loan_segment:
            conditions.append("loan_segment = :loan_segment")
            params["loan_segment"] = loan_segment

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = text(
            f"SELECT * FROM borrower_profiles {where} "
            f"ORDER BY dpd DESC, updated_at DESC LIMIT :limit OFFSET :offset"
        )

        async with self.engine.connect() as conn:
            try:
                rs = await conn.execute(sql, params)
                return [dict(row._mapping) for row in rs.fetchall()]
            except Exception:
                # Table may not exist in dev environments without borrower profiles seeded
                return []

    async def get_borrower_profile(self, user_id: str) -> dict | None:
        """Return the borrower profile for a specific user_id."""
        sql = text("SELECT * FROM borrower_profiles WHERE user_id = :user_id LIMIT 1")
        async with self.engine.connect() as conn:
            try:
                rs = await conn.execute(sql, {"user_id": user_id})
                row = rs.fetchone()
                return dict(row._mapping) if row else None
            except Exception:
                return None

