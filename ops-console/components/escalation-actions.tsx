"use client";

import { useState } from "react";
import { API_BASE } from "./api";

export function EscalationActions({ escalationId }: { escalationId: string }) {
  const [status, setStatus] = useState("open");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  async function submit(nextStatus: string) {
    setSaving(true);
    setMessage("");
    try {
      const res = await fetch(`${API_BASE}/escalations/${escalationId}/actions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ operator: "ops-console", status: nextStatus, notes }),
      });
      if (!res.ok) throw new Error(String(res.status));
      setStatus(nextStatus);
      setMessage("saved");
    } catch {
      setMessage("failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
      <input
        aria-label="notes"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="operator notes"
        style={{ padding: "4px 8px", borderRadius: 6, border: "1px solid #cfd6d8" }}
      />
      <button disabled={saving} onClick={() => submit("in_progress")}>Start</button>
      <button disabled={saving} onClick={() => submit("closed")}>Resolve</button>
      <span className="badge">{status}</span>
      {message ? <span>{message}</span> : null}
    </div>
  );
}
