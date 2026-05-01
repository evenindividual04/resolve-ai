import React from "react";
import { useCurrentFrame, interpolate } from "remotion";

export const SolutionScene: React.FC = () => {
  const frame = useCurrentFrame();

  const headerOpacity = interpolate(frame, [0, 20], [0, 1]);
  const check1Opacity = interpolate(frame, [10, 30], [0, 1]);
  const check2Opacity = interpolate(frame, [20, 40], [0, 1]);
  const check3Opacity = interpolate(frame, [30, 50], [0, 1]);

  return (
    <div
      style={{
        flex: 1,
        backgroundColor: "#0a0a0a",
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
        The Resolve AI Solution
      </h1>
      <div style={{ marginTop: 60 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            marginBottom: 30,
            opacity: check1Opacity,
          }}
        >
          <span style={{ color: "#22c55e", fontSize: 40, marginRight: 20 }}>✓</span>
          <span style={{ color: "#e5e7eb", fontSize: 28 }}>
            Predictable workflow execution under strict policy constraints
          </span>
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            marginBottom: 30,
            opacity: check2Opacity,
          }}
        >
          <span style={{ color: "#22c55e", fontSize: 40, marginRight: 20 }}>✓</span>
          <span style={{ color: "#e5e7eb", fontSize: 28 }}>
            Full auditability for every model decision and action
          </span>
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            opacity: check3Opacity,
          }}
        >
          <span style={{ color: "#22c55e", fontSize: 40, marginRight: 20 }}>✓</span>
          <span style={{ color: "#e5e7eb", fontSize: 28 }}>
            Resilient handling of ambiguity, failure, and abuse
          </span>
        </div>
      </div>
    </div>
  );
};