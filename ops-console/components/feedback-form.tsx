"use client";

import { useState } from "react";
import { API_BASE } from "./api";
import { RatingPicker } from "./RatingPicker";
import { useToast } from "./ToastContext";

export function FeedbackForm() {
  const [workflowId, setWorkflowId] = useState("");
  const [signalType, setSignalType] = useState("good_decision");
  const [rating, setRating] = useState(4);
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const { toast } = useToast();

  async function submit() {
    const trimmedId = workflowId.trim();

    if (!trimmedId) {
      setError("Workflow ID is required.");
      return;
    }

    setSaving(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ workflow_id: trimmedId, signal_type: signalType, rating, notes }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      toast({ variant: "success", title: "Feedback submitted", message: `Signal "${signalType}" recorded for ${trimmedId}.` });
      setWorkflowId("");
      setNotes("");
      setRating(4);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Network error";
      setError(`Failed to submit: ${msg}`);
      toast({ variant: "error", title: "Submission failed", message: msg });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="card stack">
      <div className="section-header">
        <div>
          <div className="h6">Learning loop</div>
          <h2 className="section-title">Submit feedback signal</h2>
        </div>
      </div>

      {error && <div className="form-error">{error}</div>}

      <div className="stack">
        <label className="stack">
          <span className="subtle">Workflow ID</span>
          <input
            id="feedback-workflow-id"
            placeholder="workflow_id"
            value={workflowId}
            onChange={(e) => setWorkflowId(e.target.value)}
            aria-required="true"
          />
        </label>

        <div className="field-row">
          <label className="stack">
            <span className="subtle">Signal type</span>
            <select id="feedback-signal-type" value={signalType} onChange={(e) => setSignalType(e.target.value)}>
              <option value="good_decision">good_decision</option>
              <option value="bad_decision">bad_decision</option>
              <option value="operator_override">operator_override</option>
              <option value="policy_gap">policy_gap</option>
            </select>
          </label>

          <label className="stack">
            <span className="subtle">Rating</span>
            <RatingPicker value={rating} onChange={setRating} disabled={saving} />
          </label>
        </div>

        <label className="stack">
          <span className="subtle">Notes</span>
          <textarea
            id="feedback-notes"
            placeholder="What should the system learn from this?"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={5}
          />
        </label>

        <div className="hero-actions mt-0">
          <button id="feedback-submit-btn" onClick={submit} disabled={saving}>
            {saving ? "Submitting…" : "Submit signal"}
          </button>
        </div>
      </div>
    </div>
  );
}
