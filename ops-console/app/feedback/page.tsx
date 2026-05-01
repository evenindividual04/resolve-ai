import { fetchJson } from "../../components/api";
import { FeedbackForm } from "../../components/feedback-form";

type Feedback = {
  workflow_id: string;
  signal_type: string;
  rating: number;
  notes: string;
  created_at: string;
};

export default async function FeedbackPage() {
  const rows = await fetchJson<Feedback[]>("/feedback").catch(() => []);
  return (
    <div className="grid">
      <section style={{ gridColumn: "span 12" }}>
        <FeedbackForm />
      </section>
      <section className="card" style={{ gridColumn: "span 12" }}>
        <div className="h6">Recent Feedback Signals</div>
        {rows.slice(0, 30).map((r, idx) => (
          <div className="row" key={`${r.workflow_id}-${idx}`}>
            <span>{r.workflow_id} {r.signal_type} ({r.rating})</span>
            <span>{r.created_at}</span>
          </div>
        ))}
      </section>
    </div>
  );
}
