import type { NegotiationState } from "../types";

interface NegotiationPanelProps {
  negotiation: NegotiationState;
  maxTurns?: number;
}

function fmt(n: number): string {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(n);
}

export function NegotiationPanel({ negotiation, maxTurns = 8 }: NegotiationPanelProps) {
  const { turn_count, prior_offers, counter_offer_amount, negotiated_amount, outstanding_amount, strike_count } = negotiation;
  const turnPressure = maxTurns > 0 ? turn_count / maxTurns : 0;

  function turnSegmentClass(idx: number): string {
    if (idx >= turn_count) return "turn-segment";
    if (turnPressure >= 0.85) return "turn-segment danger used";
    if (turnPressure >= 0.6) return "turn-segment warn used";
    return "turn-segment used";
  }

  return (
    <div className="stack" style={{ gap: 18 }}>
      {/* Turn budget */}
      <div className="stack" style={{ gap: 8 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span className="h6">Turn budget</span>
          <span className="subtle" style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem" }}>
            {turn_count} / {maxTurns}
          </span>
        </div>
        <div className="turn-track">
          {Array.from({ length: maxTurns }).map((_, i) => (
            <span key={i} className={turnSegmentClass(i)} aria-hidden="true" />
          ))}
        </div>
      </div>

      {/* Key amounts */}
      <div className="panel-grid" style={{ gridTemplateColumns: "repeat(2, 1fr)" }}>
        <div className="metric-card">
          <span className="metric-label h6">Outstanding</span>
          <div className="metric-value" style={{ fontSize: "1.1rem" }}>{fmt(outstanding_amount)}</div>
        </div>
        {negotiated_amount != null ? (
          <div className="metric-card">
            <span className="metric-label h6">Agreed settlement</span>
            <div className="metric-value" style={{ fontSize: "1.1rem", color: "var(--ok)" }}>{fmt(negotiated_amount)}</div>
          </div>
        ) : counter_offer_amount != null ? (
          <div className="metric-card">
            <span className="metric-label h6">Counter-offer</span>
            <div className="metric-value" style={{ fontSize: "1.1rem", color: "var(--info)" }}>{fmt(counter_offer_amount)}</div>
          </div>
        ) : (
          <div className="metric-card">
            <span className="metric-label h6">Counter-offer</span>
            <div className="subtle" style={{ fontSize: "0.88rem" }}>Pending</div>
          </div>
        )}
      </div>

      {/* Strike count */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span className="h6">Strikes</span>
        <div style={{ display: "flex", gap: 4 }}>
          {Array.from({ length: 3 }).map((_, i) => (
            <span key={i} className="strike-icon">{i < strike_count ? "⚡" : "○"}</span>
          ))}
        </div>
        {strike_count >= 3 && (
          <span className="status-chip danger" style={{ fontSize: "0.78rem" }}>Escalation risk</span>
        )}
      </div>

      {/* Prior offers */}
      {prior_offers.length > 0 && (
        <div className="stack" style={{ gap: 8 }}>
          <span className="h6">Borrower offer history</span>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            {prior_offers.map((offer, i) => (
              <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                <span className="offer-dot" title={fmt(offer)}>
                  {i + 1}
                </span>
                <span className="subtle" style={{ fontSize: "0.75rem", fontFamily: "var(--font-mono)" }}>
                  {fmt(offer)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
