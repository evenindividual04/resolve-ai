type StatusVariant = "ok" | "warn" | "danger" | "info" | "halted";

interface StatusBadgeProps {
  variant: StatusVariant;
  children: React.ReactNode;
  className?: string;
}

export function StatusBadge({ variant, children, className = "" }: StatusBadgeProps) {
  return (
    <span className={`status-chip ${variant} ${className}`.trim()}>
      {children}
    </span>
  );
}

export function workflowStateVariant(state: string): StatusVariant {
  switch (state) {
    case "resolved":           return "ok";
    case "negotiating":        return "info";
    case "waiting_for_payment": return "warn";
    case "payment_failed":     return "danger";
    case "escalated":          return "danger";
    case "halted":             return "halted";
    case "contacted":          return "info";
    case "revalidation_required": return "warn";
    default:                   return "info";
  }
}

export function eventTypeVariant(type: string, payload?: Record<string, unknown>): StatusVariant {
  switch (type) {
    case "payment_webhook":
      return payload?.status === "paid" ? "ok" : "danger";
    case "scheduler_timeout": return "warn";
    case "channel_switch":    return "info";
    case "user_message":      return "info";
    default:                  return "info";
  }
}
