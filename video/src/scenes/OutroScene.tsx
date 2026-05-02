import React from "react";
import { useCurrentFrame, interpolate } from "remotion";

export const OutroScene: React.FC = () => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 30], [0, 1]);
  const subtitleOpacity = interpolate(frame, [20, 50], [0, 1]);
  const glowOpacity = interpolate(frame, [30, 60], [0, 0.5]);

  return (
    <div
      style={{
        flex: 1,
        backgroundColor: "#0B1121",
        justifyContent: "center",
        alignItems: "center",
        display: "flex",
        flexDirection: "column",
        padding: 100,
        fontFamily: 'system-ui, -apple-system, sans-serif'
      }}
    >
      <div style={{
        position: 'absolute',
        width: 800,
        height: 800,
        background: 'radial-gradient(circle, rgba(16,185,129,0.3) 0%, rgba(11,17,33,0) 70%)',
        opacity: glowOpacity,
      }} />

      <h1
        style={{
          color: "#ffffff",
          fontSize: 100,
          fontWeight: 800,
          margin: 0,
          opacity: titleOpacity,
          letterSpacing: "-0.04em",
          zIndex: 10
        }}
      >
        Resolve AI
      </h1>
      <p
        style={{
          color: "#10b981",
          fontSize: 40,
          fontWeight: 400,
          marginTop: 24,
          opacity: subtitleOpacity,
          zIndex: 10,
          letterSpacing: "-0.01em"
        }}
      >
        The AI-Native Bank starts here.
      </p>
    </div>
  );
};