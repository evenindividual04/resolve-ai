interface HaltedBannerProps {
  reason?: string;
}

export function HaltedBanner({ reason }: HaltedBannerProps) {
  const isDnc = reason?.toLowerCase().includes("dnc");
  const isLegal = reason?.toLowerCase().includes("legal");

  const title = isDnc
    ? "Workflow HALTED — DNC Violation"
    : isLegal
    ? "Workflow HALTED — Legal Escalation"
    : "Workflow HALTED";

  const guidance = isDnc
    ? "Do Not Contact flag is active. No agent contact is permitted under TRAI regulations. Route this case to the compliance team."
    : isLegal
    ? "Case has been referred to the legal team. All AI negotiation has been suspended. Do not contact the borrower."
    : "This workflow has been halted by the compliance layer. No further agent actions are permitted.";

  return (
    <div className="halted-banner" role="alert" aria-label="Halted workflow warning">
      <span className="halted-banner-icon" aria-hidden="true">⊘</span>
      <div className="halted-banner-body">
        <div className="halted-banner-title">{title}</div>
        <div className="halted-banner-msg">{guidance}</div>
        {reason && (
          <div className="halted-banner-msg" style={{ marginTop: 4, opacity: 0.7 }}>
            Reason recorded: <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem" }}>{reason}</span>
          </div>
        )}
      </div>
    </div>
  );
}
