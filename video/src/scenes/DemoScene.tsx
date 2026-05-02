import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";

export const DemoScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Animations
  const shellSlide = spring({ frame: frame - 10, fps, from: 100, to: 0, durationInFrames: 30 });
  const shellOpacity = interpolate(frame, [10, 30], [0, 1]);
  
  const clickScale = spring({ frame: frame - 120, fps, from: 1, to: 0.98, durationInFrames: 10, config: { damping: 10 } });
  const clickRelease = spring({ frame: frame - 130, fps, from: 0.98, to: 1, durationInFrames: 10, config: { damping: 10 } });
  const finalScale = frame > 130 ? clickRelease : clickScale;

  const panelSlide = spring({ frame: frame - 140, fps, from: 100, to: 0, durationInFrames: 25 });
  const panelOpacity = interpolate(frame, [140, 160], [0, 1]);

  const items = [
    { id: "cust-003", segment: "business", risk: "CRITICAL", amount: "₹800", status: "Legal Escalation", color: "#facc15" },
    { id: "cust-dnc", segment: "personal", risk: "MEDIUM", amount: "₹400", status: "DNC — No Contact", color: "#c084fc" },
  ];

  return (
    <div style={{ flex: 1, backgroundColor: "#0B1121", padding: "60px 100px", fontFamily: 'system-ui, -apple-system, sans-serif', display: 'flex', flexDirection: 'column' }}>
      
      <div style={{ opacity: shellOpacity, transform: `translateY(${shellSlide}px)`, display: 'flex', flexDirection: 'column', gap: 16 }}>
        <h1 style={{ color: "#fff", fontSize: 48, fontWeight: 700, margin: 0 }}>Ops Console</h1>
        <p style={{ color: "#9ca3af", fontSize: 24, margin: 0 }}>Triage-first observability.</p>
      </div>

      <div style={{
        marginTop: 40,
        flex: 1,
        background: '#111827',
        borderRadius: 24,
        border: '1px solid #374151',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
        display: 'flex',
        overflow: 'hidden',
        opacity: shellOpacity,
        transform: `translateY(${shellSlide}px)`,
      }}>
        {/* Main Content Area */}
        <div style={{ flex: 1, padding: 40, display: 'flex', flexDirection: 'column', gap: 24 }}>
          <div style={{ fontSize: 24, fontWeight: 600, color: '#fff', marginBottom: 16 }}>Workflow Ledger</div>
          
          {items.map((item, i) => {
            const isClickedRow = i === 0;
            const rowPop = spring({ frame: frame - 40 - (i * 15), fps, from: 0, to: 1, durationInFrames: 20 });
            return (
              <div key={item.id} style={{
                background: '#1f2937',
                borderRadius: 12,
                padding: 24,
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                borderLeft: `6px solid ${item.color}`,
                transform: `scale(${isClickedRow ? finalScale * rowPop : rowPop})`,
                opacity: rowPop,
              }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div style={{ color: '#fff', fontSize: 20, fontFamily: 'monospace' }}>{item.id}</div>
                  <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                    <span style={{ color: '#9ca3af', fontSize: 16, textTransform: 'uppercase' }}>{item.segment}</span>
                    <span style={{ color: '#60a5fa', fontSize: 14 }}>{item.risk}</span>
                  </div>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 8 }}>
                  <div style={{ padding: '6px 12px', borderRadius: 99, border: `1px solid ${item.color}`, color: item.color, fontSize: 14, fontWeight: 600 }}>{item.status}</div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Sliding Trace Panel */}
        <div style={{
          width: 500,
          background: '#0f172a',
          borderLeft: '1px solid #374151',
          padding: 40,
          display: 'flex',
          flexDirection: 'column',
          transform: `translateX(${panelSlide}px)`,
          opacity: panelOpacity
        }}>
          <div style={{ color: '#fff', fontSize: 24, fontWeight: 600, marginBottom: 24 }}>Decision Trace</div>
          <div style={{ display: 'flex', gap: 12, marginBottom: 32 }}>
            <span style={{ background: '#374151', padding: '4px 12px', borderRadius: 6, color: '#e5e7eb', fontSize: 14 }}>Turn 4</span>
            <span style={{ background: '#ef4444', padding: '4px 12px', borderRadius: 6, color: '#fff', fontSize: 14, fontWeight: 600 }}>HALTED</span>
          </div>
          <div style={{ background: '#1e293b', padding: 24, borderRadius: 12, border: '1px solid #334155' }}>
            <div style={{ color: '#94a3b8', fontSize: 14, marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>LLM Extraction</div>
            <pre style={{ margin: 0, color: '#818cf8', fontSize: 16, fontFamily: 'monospace', lineHeight: 1.5 }}>
{`{
  "intent": "refusal_legal",
  "entities": {
    "lawyer_mentioned": true
  },
  "confidence": 0.99
}`}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};