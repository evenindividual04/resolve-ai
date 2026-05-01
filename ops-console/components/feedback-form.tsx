"use client";

import { useState } from "react";
import { API_BASE } from "./api";

export function FeedbackForm() {
  const [workflowId, setWorkflowId] = useState("");
  const [signalType, setSignalType] = useState("good_decision");
  const [rating, setRating] = useState(4);
  const [notes, setNotes] = useState("");
  const [status, setStatus] = useState("");

  async function submit() {
    setStatus("");
    const res = await fetch(`${API_BASE}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workflow_id: workflowId, signal_type: signalType, rating, notes }),
    });
    setStatus(res.ok ? "saved" : "failed");
  }

  return (
    <div className="card">
      <div className="h6">Submit Feedback Signal</div>
      <div className="row"><input placeholder="workflow_id" value={workflowId} onChange={(e) => setWorkflowId(e.target.value)} /></div>
      <div className="row">
        <select value={signalType} onChange={(e) => setSignalType(e.target.value)}>
          <option value="good_decision">good_decision</option>
          <option value="bad_decision">bad_decision</option>
          <option value="operator_override">operator_override</option>
          <option value="policy_gap">policy_gap</option>
        </select>
        <input type="number" min={1} max={5} value={rating} onChange={(e) => setRating(Number(e.target.value))} />
      </div>
      <div className="row"><input placeholder="notes" value={notes} onChange={(e) => setNotes(e.target.value)} /></div>
      <div className="row"><button onClick={submit}>Submit</button><span>{status}</span></div>
    </div>
  );
}
