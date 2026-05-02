import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";

export const TitleScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleOpacity = interpolate(frame, [0, 30], [0, 1]);
  const subtitleOpacity = interpolate(frame, [15, 45], [0, 1]);
  const slideUp = spring({
    frame: frame - 20,
    fps,
    from: 60,
    to: 0,
    durationInFrames: 40,
    config: { damping: 14 }
  });
  const glowOpacity = interpolate(frame, [30, 60], [0, 0.4]);

  return (
    <div
      style={{
        flex: 1,
        backgroundColor: "#0B1121",
        justifyContent: "center",
        alignItems: "center",
        display: "flex",
        flexDirection: "column",
        fontFamily: 'system-ui, -apple-system, sans-serif'
      }}
    >
      {/* Background Glow */}
      <div style={{
        position: 'absolute',
        width: 800,
        height: 800,
        background: 'radial-gradient(circle, rgba(37,99,235,0.4) 0%, rgba(11,17,33,0) 70%)',
        opacity: glowOpacity,
        transform: `translateY(${slideUp * 0.5}px)`,
      }} />

      <h1
        style={{
          color: "#ffffff",
          fontSize: 130,
          fontWeight: 800,
          margin: 0,
          opacity: titleOpacity,
          transform: `translateY(${slideUp}px)`,
          textAlign: "center",
          letterSpacing: "-0.04em",
          zIndex: 10,
          textShadow: '0 10px 30px rgba(0,0,0,0.5)'
        }}
      >
        Resolve AI
      </h1>
      <h2
        style={{
          color: "#9ca3af",
          fontSize: 38,
          fontWeight: 400,
          marginTop: 24,
          opacity: subtitleOpacity,
          transform: `translateY(${slideUp * 0.8}px)`,
          zIndex: 10,
          letterSpacing: "-0.01em"
        }}
      >
        Autonomous Collections <span style={{ color: '#60a5fa' }}>Intelligence</span>
      </h2>
    </div>
  );
};