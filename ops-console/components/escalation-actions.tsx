"use client";

import { useState } from "react";
import { API_BASE } from "./api";
import { useToast } from "./ToastContext";

export function EscalationActions({ escalationId, initialStatus }: { escalationId: string; initialStatus: string }) {
  const [status, setStatus] = useState(initialStatus);
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [lastAttemptedStatus, setLastAttemptedStatus] = useState<string | null>(null);
  const { toast } = useToast();

  async function submit(nextStatus: string) {
    // Idempotency: prevent duplicate POSTs with the same target status
    if (saving || nextStatus === lastAttemptedStatus) return;
    setSaving(true);
    setLastAttemptedStatus(nextStatus);

    try {
      const res = await fetch(`${API_BASE}/escalations/${encodeURIComponent(escalationId)}/actions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ operator: "ops-console", status: nextStatus, notes }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      setStatus(nextStatus);
      toast({
        variant: "success",
        title: nextStatus === "closed" ? "Escalation resolved" : "Status updated",
        message: `Escalation moved to ${nextStatus.replace("_", " ")}.`,
      });
    } catch (err) {
      setLastAttemptedStatus(null); // allow retry
      toast({
        variant: "error",
        title: "Action failed",
        message: err instanceof Error ? err.message : "Could not update escalation. Try again.",
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="stack">
      <div className="section-header">
        <div className="h6">Operator actions</div>
        <span className={`status-chip ${status === "closed" ? "ok" : status === "in_progress" ? "warn" : "info"}`}>
          {saving ? "Saving…" : status.split("_").join(" ")}
        </span>
      </div>

      <textarea
        aria-label="Operator notes"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Capture what changed, why the escalation moved, and any follow-up needed."
        rows={3}
      />

      <div className="hero-actions mt-0">
        <button
          className="secondary"
          disabled={saving || status === "closed"}
          onClick={() => submit("in_progress")}
        >
          Start
        </button>
        <button
          disabled={saving || status === "closed"}
          onClick={() => submit("closed")}
        >
          {saving ? "Saving…" : "Resolve"}
        </button>
      </div>

      {status === "closed" && (
        <div className="subtle" style={{ fontSize: "0.88rem" }}>
          This escalation is closed.
        </div>
      )}
    </div>
  );
}
