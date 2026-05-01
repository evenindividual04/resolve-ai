"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import type { WorkflowSummary } from "../../types";
import { StatusBadge, workflowStateVariant } from "../../components/StatusBadge";
import { EmptyState } from "../../components/EmptyState";
import { timeAgo, fmtINR } from "../../components/utils";

type FilterState = "all" | "negotiating" | "waiting_for_payment" | "resolved" | "escalated" | "halted";

const FILTER_OPTIONS: { label: string; value: FilterState; chipClass?: string }[] = [
  { label: "All", value: "all" },
  { label: "Negotiating", value: "negotiating" },
  { label: "Waiting payment", value: "waiting_for_payment" },
  { label: "Resolved", value: "resolved", chipClass: "ok" },
  { label: "Escalated", value: "escalated", chipClass: "danger" },
  { label: "Halted", value: "halted", chipClass: "halted" },
];

interface WorkflowsClientProps {
  workflows: WorkflowSummary[];
}

export function WorkflowsClient({ workflows }: WorkflowsClientProps) {
  const [filter, setFilter] = useState<FilterState>("all");
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    return workflows.filter((w) => {
      const matchesState = filter === "all" || w.state === filter;
      const matchesSearch = !search || w.workflow_id.toLowerCase().includes(search.toLowerCase()) || w.user_id?.toLowerCase().includes(search.toLowerCase());
      return matchesState && matchesSearch;
    });
  }, [workflows, filter, search]);

  return (
    <>
      <div className="section-header" style={{ marginBottom: 16 }}>
        <nav className="filter-row">
          {FILTER_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              className={`filter-chip${filter === opt.value ? ` active${opt.chipClass ? ` ${opt.chipClass}` : ""}` : ""}`}
              onClick={() => setFilter(opt.value)}
            >
              {opt.label}
            </button>
          ))}
        </nav>
        <input
          placeholder="Search workflow ID or user…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ maxWidth: 220, padding: "7px 12px" }}
          aria-label="Search workflows"
        />
      </div>

      <div className="card-stack">
        {filtered.length === 0 ? (
          <EmptyState icon="○" title="No workflows match" message={`No workflows match the current filter and search.`} />
        ) : (
          filtered.map((w) => (
            <div
              key={w.workflow_id}
              className={`list-item ${w.state === "halted" ? "borrower-dnc-row" : ""}`}
            >
              <div>
                <div>
                  <Link href={`/workflows/${w.workflow_id}`} style={{ fontFamily: "var(--font-mono)", fontSize: "0.9rem" }}>
                    {w.workflow_id}
                  </Link>
                </div>
                <div className="subtle" style={{ fontSize: "0.82rem" }}>
                  {w.loan_segment?.replace(/_/g, " ")} ·{" "}
                  {w.risk_band && <span className={`risk-band-${w.risk_band}`}>{w.risk_band}</span>} ·{" "}
                  Turn {w.turn_count} ·{" "}
                  {timeAgo(w.updated_at)}
                </div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}>
                <StatusBadge variant={workflowStateVariant(w.state)}>
                  {w.state.replace(/_/g, " ")}
                </StatusBadge>
                <span className="subtle" style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem" }}>
                  {fmtINR(w.outstanding_amount)}
                </span>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="subtle" style={{ marginTop: 12, fontSize: "0.85rem" }}>
        Showing {filtered.length} of {workflows.length} workflows
      </div>
    </>
  );
}
