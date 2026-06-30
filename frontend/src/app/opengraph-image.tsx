import { ImageResponse } from "next/og";

export const alt = "Certo — The trust layer for AI agents";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OG() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%", height: "100%", display: "flex", flexDirection: "column",
          justifyContent: "space-between", padding: 72,
          background: "radial-gradient(120% 120% at 20% -10%, #1b1640 0%, #0b0b12 55%, #070709 100%)",
          color: "white", fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
          <div style={{ width: 56, height: 56, borderRadius: 14, display: "flex", alignItems: "center", justifyContent: "center", background: "linear-gradient(135deg,#7c6cff,#22d3ee)", fontSize: 34 }}>🛡️</div>
          <div style={{ fontSize: 34, fontWeight: 700, display: "flex" }}>Certo</div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 16, fontSize: 68, fontWeight: 700, lineHeight: 1.05, maxWidth: 960 }}>
            <span>Ship AI agents</span>
            <span style={{ background: "linear-gradient(90deg,#a78bfa,#22d3ee)", backgroundClip: "text", color: "transparent" }}>you can trust.</span>
          </div>
          <div style={{ display: "flex", fontSize: 30, color: "rgba(255,255,255,0.6)", maxWidth: 880 }}>
            Automated security &amp; reliability audits, an explainable Trust Score, and a shareable certificate.
          </div>
        </div>

        <div style={{ display: "flex", gap: 14, fontSize: 24, color: "rgba(255,255,255,0.55)" }}>
          {["OWASP", "NIST AI RMF", "EU AI Act", "ISO 42001"].map((s) => (
            <span key={s} style={{ display: "flex", border: "1px solid rgba(255,255,255,0.18)", borderRadius: 999, padding: "8px 20px" }}>{s}</span>
          ))}
        </div>
      </div>
    ),
    { ...size },
  );
}
