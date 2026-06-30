"use client";

import { motion } from "framer-motion";
import { scoreTone } from "@/lib/trust";
import { cn } from "@/lib/utils";

const TONE_COLOR = {
  success: "hsl(142 71% 45%)",
  warning: "hsl(38 92% 50%)",
  danger: "hsl(0 72% 55%)",
} as const;

export function TrustRing({
  score,
  size = 150,
  stroke = 11,
  label = "Trust Score",
  potential,
  className,
}: {
  score: number;
  size?: number;
  stroke?: number;
  label?: string;
  potential?: number;
  className?: string;
}) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const tone = scoreTone(score);
  const color = TONE_COLOR[tone];
  const offset = c - (score / 100) * c;
  const potOffset = potential !== undefined ? c - (potential / 100) * c : 0;

  return (
    <div className={cn("relative inline-flex items-center justify-center", className)} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="hsl(var(--border))" strokeWidth={stroke} />
        {potential !== undefined && (
          <motion.circle
            cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeOpacity={0.25}
            strokeWidth={stroke} strokeLinecap="round" strokeDasharray={c}
            initial={{ strokeDashoffset: c }} whileInView={{ strokeDashoffset: potOffset }}
            viewport={{ once: true }} transition={{ duration: 1.1, ease: [0.16, 1, 0.3, 1] }}
          />
        )}
        <motion.circle
          cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color}
          strokeWidth={stroke} strokeLinecap="round" strokeDasharray={c}
          initial={{ strokeDashoffset: c }} whileInView={{ strokeDashoffset: offset }}
          viewport={{ once: true }} transition={{ duration: 1.1, ease: [0.16, 1, 0.3, 1] }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <motion.span
          className="font-mono font-semibold tracking-tight"
          style={{ fontSize: size / 4 }}
          initial={{ opacity: 0 }} whileInView={{ opacity: 1 }} viewport={{ once: true }} transition={{ delay: 0.3 }}
        >
          {score.toFixed(0)}
        </motion.span>
        {label && (
          <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">{label}</span>
        )}
        {potential !== undefined && (
          <span className="mt-0.5 text-[10px] text-accent">↑ {potential.toFixed(0)} potential</span>
        )}
      </div>
    </div>
  );
}
