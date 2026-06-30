"use client";

import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, PolarAngleAxis, PolarGrid,
  Radar, RadarChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import type { CategoryScore, TrendPoint } from "@/lib/types";

const ACCENT = "hsl(243 75% 59%)";
const CYAN = "hsl(189 94% 43%)";

const axis = { tick: { fill: "hsl(215 16% 47%)", fontSize: 11 }, tickLine: false, axisLine: false } as const;

function TipBox({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border bg-background/95 px-3 py-2 text-xs shadow-lg backdrop-blur">
      {label && <p className="mb-1 font-medium text-foreground">{label}</p>}
      {payload.map((p: any) => (
        <p key={p.dataKey} className="flex items-center gap-2 text-muted-foreground">
          <span className="inline-block size-2 rounded-full" style={{ background: p.color }} />
          {p.name}: <span className="font-mono font-medium text-foreground">{typeof p.value === "number" ? p.value.toLocaleString("en-US") : p.value}</span>
        </p>
      ))}
    </div>
  );
}

export function TrustTrendChart({ data, height = 240 }: { data: TrendPoint[]; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <defs>
          <linearGradient id="trustFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={ACCENT} stopOpacity={0.35} />
            <stop offset="100%" stopColor={ACCENT} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(214 32% 91%)" vertical={false} />
        <XAxis dataKey="label" {...axis} minTickGap={24} />
        <YAxis domain={[40, 100]} {...axis} width={32} />
        <Tooltip content={<TipBox />} />
        <Area type="monotone" dataKey="trust" name="Trust Score" stroke={ACCENT} strokeWidth={2.5} fill="url(#trustFill)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function TaskVolumeChart({ data, height = 240 }: { data: TrendPoint[]; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(214 32% 91%)" vertical={false} />
        <XAxis dataKey="label" {...axis} minTickGap={24} />
        <YAxis {...axis} width={32} />
        <Tooltip content={<TipBox />} cursor={{ fill: "hsl(210 40% 96%)" }} />
        <Bar dataKey="tasks" name="Tasks" radius={[3, 3, 0, 0]} fill={CYAN} maxBarSize={18} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function CategoryRadar({ categories, height = 260 }: { categories: CategoryScore[]; height?: number }) {
  const data = categories.map((c) => ({ category: c.label, score: c.score }));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RadarChart data={data} outerRadius="72%">
        <PolarGrid stroke="hsl(214 32% 88%)" />
        <PolarAngleAxis dataKey="category" tick={{ fill: "hsl(215 16% 42%)", fontSize: 11 }} />
        <Radar name="Score" dataKey="score" stroke={ACCENT} fill={ACCENT} fillOpacity={0.25} strokeWidth={2} />
        <Tooltip content={<TipBox />} />
      </RadarChart>
    </ResponsiveContainer>
  );
}

export function MiniSparkline({ data, height = 38, color = ACCENT }: { data: TrendPoint[]; height?: number; color?: string }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={`sp-${color}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.3} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area type="monotone" dataKey="trust" stroke={color} strokeWidth={1.8} fill={`url(#sp-${color})`} />
      </AreaChart>
    </ResponsiveContainer>
  );
}
