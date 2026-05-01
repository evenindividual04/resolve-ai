import React from "react";
import { useCurrentFrame, interpolate } from "remotion";

export const ProblemScene: React.FC = () => {
  const frame = useCurrentFrame();

  const headerOpacity = interpolate(frame, [0, 20], [0, 1]);
  const contentOpacity = interpolate(frame, [15, 35], [0, 1]);
  const item1Y = interpolate(frame, [20, 40], [50, 0]);
  const item2Y = interpolate(frame, [30, 50], [50, 0]);
  const item3Y = interpolate(frame, [40, 60], [50, 0]);

  return (
    <div
      style={{
        flex: 1,
        backgroundColor: "#111827",
        justifyContent: "center",
        alignItems: "flex-start",
        display: "flex",
        flexDirection: "column",
        padding: 100,
      }}
    >
      <h1
        style={{
          color: "#ffffff",
          fontSize: 64,
          fontWeight: 700,
          margin: 0,
          opacity: headerOpacity,
        }}
      >
        The Challenge
      </h1>
      <div
        style={{
          opacity: contentOpacity,
          marginTop: 60,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            marginBottom: 30,
            transform: `translateY(${item1Y}px)`,
          }}
        >
          <span style={{ color: "#ef4444", fontSize: 40, marginRight: 20 }}>✕</span>
          <span style={{ color: "#e5e7eb", fontSize: 28 }}>
            AI agent systems are easy to demo, hard to trust in production
          </span>
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            marginBottom: 30,
            transform: `translateY(${item2Y}px)`,
          }}
        >
          <span style={{ color: "#ef4444", fontSize: 40, marginRight: 20 }}>✕</span>
          <span style={{ color: "#e5e7eb", fontSize: 28 }}>
            No predictability for critical decision-making workflows
          </span>
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            transform: `translateY(${item3Y}px)`,
          }}
        >
          <span style={{ color: "#ef4444", fontSize: 40, marginRight: 20 }}>✕</span>
          <span style={{ color: "#e5e7eb", fontSize: 28 }}>
            Missing auditability, compliance, and reproducibility
          </span>
        </div>
      </div>
    </div>
  );
};