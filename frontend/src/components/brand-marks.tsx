import * as React from "react";

/**
 * Brand marks for the LLM providers & agent frameworks Certo works with.
 * Simplified, recognizable monochrome-on-brand-color glyphs (no trademarked
 * raster assets) — clean and professional.
 */

type MarkProps = { className?: string };

export function OpenAIMark({ className }: MarkProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" aria-hidden>
      <path d="M12 4a4 4 0 0 1 3.7 2.5 4 4 0 0 1 2.6 6.1A4 4 0 0 1 14.6 19a4 4 0 0 1-5.2 0 4 4 0 0 1-3.7-6.4 4 4 0 0 1 2.6-6.1A4 4 0 0 1 12 4Z"
        stroke="currentColor" strokeWidth="1.4" />
      <path d="M12 8v8M8.5 10l7 4M15.5 10l-7 4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" opacity=".7" />
    </svg>
  );
}

export function AnthropicMark({ className }: MarkProps) {
  // Claude-style sunburst asterisk
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden>
      <g stroke="currentColor" strokeWidth="1.7" strokeLinecap="round">
        {Array.from({ length: 8 }).map((_, i) => {
          const a = (i * Math.PI) / 4;
          return <line key={i} x1={12} y1={12} x2={12 + 8 * Math.cos(a)} y2={12 + 8 * Math.sin(a)} />;
        })}
      </g>
    </svg>
  );
}

export function GeminiMark({ className }: MarkProps) {
  // 4-point spark star (accurate Gemini glyph shape)
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden fill="currentColor">
      <path d="M12 2c.6 5.2 4.2 8.8 9.4 9.4C16.2 12 12.6 15.6 12 20.8 11.4 15.6 7.8 12 2.6 11.4 7.8 10.8 11.4 7.2 12 2Z" />
    </svg>
  );
}

export function MetaMark({ className }: MarkProps) {
  // infinity loop
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" aria-hidden>
      <path d="M4 12c0-3 1.6-5 3.8-5 2.8 0 4 5 4.2 5s1.4 5 4.2 5C18.4 17 20 15 20 12s-1.6-5-3.8-5C13.4 7 12.2 12 12 12s-1.4 5-4.2 5C5.6 17 4 15 4 12Z"
        stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

export function MistralMark({ className }: MarkProps) {
  // stacked stripes
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden fill="currentColor">
      <rect x="4" y="5" width="16" height="3" rx="1" opacity="1" />
      <rect x="4" y="10.5" width="16" height="3" rx="1" opacity=".75" />
      <rect x="4" y="16" width="16" height="3" rx="1" opacity=".5" />
    </svg>
  );
}

export function GrokMark({ className }: MarkProps) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
      <path d="M6 5l12 14M18 5L6 19" />
    </svg>
  );
}

export interface Provider { name: string; color: string; Mark: (p: MarkProps) => React.ReactElement }

export const PROVIDERS: Provider[] = [
  { name: "OpenAI", color: "#10a37f", Mark: OpenAIMark },
  { name: "Anthropic", color: "#d97757", Mark: AnthropicMark },
  { name: "Google Gemini", color: "#4285f4", Mark: GeminiMark },
  { name: "Meta Llama", color: "#0866ff", Mark: MetaMark },
  { name: "Mistral", color: "#fa520f", Mark: MistralMark },
  { name: "xAI Grok", color: "#0b0b0b", Mark: GrokMark },
];

/** A branded tile: rounded square with the brand color + white glyph. */
export function BrandTile({ provider, size = 44, label = false, className = "" }: { provider: Provider; size?: number; label?: boolean; className?: string }) {
  const { Mark } = provider;
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <span
        className="grid place-items-center rounded-xl text-white shadow-sm"
        style={{ width: size, height: size, background: provider.color, boxShadow: `0 6px 20px -8px ${provider.color}` }}
      >
        <Mark className="size-[55%]" />
      </span>
      {label && <span className="text-sm font-medium">{provider.name}</span>}
    </span>
  );
}

/* ── Agent frameworks (colored chips with glyph) ── */
export interface FW { name: string; color: string; glyph: string }
export const FRAMEWORKS_BRAND: FW[] = [
  { name: "OpenAI Agents SDK", color: "#10a37f", glyph: "⬡" },
  { name: "LangGraph", color: "#1c7d4d", glyph: "🦜" },
  { name: "CrewAI", color: "#ff5a3c", glyph: "⚙" },
  { name: "PydanticAI", color: "#e91e8c", glyph: "🐍" },
  { name: "LlamaIndex", color: "#7c3aed", glyph: "🦙" },
  { name: "Autogen", color: "#2563eb", glyph: "🤖" },
];

export function FrameworkChip({ fw }: { fw: FW }) {
  return (
    <span className="inline-flex items-center gap-2 whitespace-nowrap rounded-full border bg-card px-3.5 py-1.5 text-sm font-medium shadow-sm">
      <span className="grid size-5 place-items-center rounded-md text-[11px]" style={{ background: `${fw.color}1a`, color: fw.color }}>{fw.glyph}</span>
      {fw.name}
    </span>
  );
}
