import React from "react";

type StatusChipProps = {
  variant: "ok" | "warn" | "danger" | "info" | "subtle";
  children: React.ReactNode;
  className?: string;
};

export function StatusChip({ variant, children, className = "" }: StatusChipProps) {
  return (
    <span
      className={`status-chip ${variant} ${className}`}
      role="status"
      aria-live="polite"
    >
      {children}
    </span>
  );
}
