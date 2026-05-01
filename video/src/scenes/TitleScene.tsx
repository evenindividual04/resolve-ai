import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";

export const TitleScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleOpacity = interpolate(frame, [0, 30], [0, 1]);
  const subtitleOpacity = interpolate(frame, [15, 45], [0, 1]);
  const slideUp = spring({
    frame: frame - 30,
    fps,
    from: 100,
    to: 0,
    durationInFrames: 30,
  });

  return (
    <div
      style={{
        flex: 1,
        backgroundColor: "#0a0a0a",
        justifyContent: "center",
        alignItems: "center",
        display: "flex",
        flexDirection: "column",
        padding: 100,
      }}
    >
      <h1
        style={{
          color: "#ffffff",
          fontSize: 120,
          fontWeight: 800,
          margin: 0,
          opacity: titleOpacity,
          transform: `translateY(${slideUp}px)`,
          textAlign: "center",
          letterSpacing: -2,
        }}
      >
        Resolve AI
      </h1>
      <h2
        style={{
          color: "#60a5fa",
          fontSize: 36,
          fontWeight: 400,
          marginTop: 20,
          opacity: subtitleOpacity,
        }}
      >
        Production-Grade AI Workflow Platform for High-Stakes Negotiation
      </h2>
    </div>
  );
};