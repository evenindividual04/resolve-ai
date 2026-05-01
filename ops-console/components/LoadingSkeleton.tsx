import React from "react";

type SkeletonProps = {
  height?: number | string;
  width?: number | string;
  borderRadius?: number;
  marginBottom?: number;
};

function SkeletonLine({ height = 12, width = "100%", borderRadius = 8, marginBottom = 12 }: SkeletonProps) {
  return (
    <div
      style={{
        height,
        width,
        borderRadius,
        marginBottom,
        background: "rgba(255,255,255,0.04)",
        backgroundImage: "linear-gradient(90deg, transparent 25%, rgba(255,255,255,0.07) 50%, transparent 75%)",
        backgroundSize: "200% 100%",
        animation: "shimmer 1.5s infinite",
      }}
    />
  );
}

type LoadingSkeletonProps = {
  className?: string;
  count?: number;
  variant?: "text" | "card" | "avatar";
};

export function LoadingSkeleton({ className = "", count = 1, variant = "text" }: LoadingSkeletonProps) {
  const dims: Record<string, { height: number | string; width: number | string; borderRadius: number }> = {
    text: { height: 14, width: "100%", borderRadius: 6 },
    card: { height: 128, width: "100%", borderRadius: 16 },
    avatar: { height: 40, width: 40, borderRadius: 999 },
  };

  const d = dims[variant];

  return (
    <div className={className}>
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonLine key={i} {...d} marginBottom={i < count - 1 ? 12 : 0} />
      ))}
    </div>
  );
}
