import type { MessageLog } from "../types";
import { formatDate } from "./utils";

interface MessageLogPanelProps {
  messages: MessageLog[];
}

export function MessageLogPanel({ messages }: MessageLogPanelProps) {
  if (messages.length === 0) {
    return (
      <div className="subtle" style={{ padding: "16px 0" }}>
        No outbound messages recorded for this workflow.
      </div>
    );
  }

  return (
    <div className="card-stack">
      {messages.map((msg) => {
        const flagged = msg.compliance_passed === 0;
        const violations: string[] = Array.isArray(msg.violations) ? msg.violations : [];
        return (
          <div key={msg.message_id} className={`message-entry${flagged ? " flagged" : ""}`}>
            <div className="message-meta">
              <span className="status-chip info" style={{ fontSize: "0.78rem" }}>
                {msg.channel}
              </span>
              <span className="status-chip" style={{ fontSize: "0.78rem", textTransform: "capitalize" }}>
                {msg.action.replace(/_/g, " ")}
              </span>
              <span className="subtle" style={{ fontSize: "0.8rem", marginLeft: "auto" }}>
                {formatDate(msg.sent_at)}
              </span>
              {flagged ? (
                <span className="compliance-flagged">⚠ Flagged ({violations.length})</span>
              ) : (
                <span className="compliance-ok">✓ Compliant</span>
              )}
            </div>

            <div className="message-content">{msg.content}</div>

            {flagged && violations.length > 0 && (
              <div className="violation-list" aria-label="Compliance violations">
                {violations.map((v, i) => (
                  <div key={i} className="violation-item">{v}</div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
