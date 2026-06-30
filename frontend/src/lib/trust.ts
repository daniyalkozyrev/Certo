/**
 * Pure presentation helpers for trust scores: certification tiers, tone,
 * derived agent status and a synthetic monitoring trend.
 * (Replaces the old deterministic audit-engine — no mock scoring here.)
 */

import type { Evaluation } from "./api";
import type { TrendPoint } from "./types";

export type CertLevel =
  | "Uncertified"
  | "Bronze"
  | "Silver"
  | "Gold"
  | "Platinum"
  | "Diamond";

const CERT_THRESHOLDS: { level: CertLevel; min: number }[] = [
  { level: "Diamond", min: 95 },
  { level: "Platinum", min: 90 },
  { level: "Gold", min: 82 },
  { level: "Silver", min: 72 },
  { level: "Bronze", min: 60 },
  { level: "Uncertified", min: 0 },
];

export function certificationFor(score: number): CertLevel {
  return CERT_THRESHOLDS.find((t) => score >= t.min)!.level;
}

export const CERT_META: Record<CertLevel, { color: string; blurb: string }> = {
  Diamond: { color: "#22d3ee", blurb: "Top 1% — mission-critical ready" },
  Platinum: { color: "#94a3b8", blurb: "Top 5% — enterprise grade" },
  Gold: { color: "#f59e0b", blurb: "Top 15% — production ready" },
  Silver: { color: "#64748b", blurb: "Reliable for most workloads" },
  Bronze: { color: "#b45309", blurb: "Baseline certified" },
  Uncertified: { color: "#94a3b8", blurb: "Below certification threshold" },
};

export function scoreTone(score: number): "success" | "warning" | "danger" {
  if (score >= 82) return "success";
  if (score >= 68) return "warning";
  return "danger";
}

export type AgentStatus = "Healthy" | "Monitoring" | "Degraded" | "At Risk";

export const STATUS_TONE: Record<
  AgentStatus,
  "success" | "warning" | "danger" | "accent"
> = {
  Healthy: "success",
  Monitoring: "accent",
  Degraded: "warning",
  "At Risk": "danger",
};

/** Derive a coarse health status from a completed evaluation. */
export function statusFromScore(trust: number | null, passRate: number | null): AgentStatus {
  if (trust === null) return "Monitoring";
  if (trust < 60 || (passRate !== null && passRate < 0.5)) return "At Risk";
  if (trust < 72) return "Degraded";
  if (trust < 85) return "Monitoring";
  return "Healthy";
}

// ── deterministic wobble for the monitoring trend (visual only) ──────────

function hashString(str: string): number {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function mulberry32(seed: number) {
  let a = seed;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/**
 * Build a small Trust trend that lands on the current score. This is a
 * visual aid for the monitoring view — the real, authoritative number is the
 * backend's trust_score; intermediate points are illustrative until we persist
 * historical evaluations.
 */
export function buildTrend(
  seed: string,
  current: number,
  points = 30,
  baseTasks = 60,
): TrendPoint[] {
  const rng = mulberry32(hashString(seed));
  const out: TrendPoint[] = [];
  let trust = Math.max(40, current - 8);
  for (let i = points - 1; i >= 0; i--) {
    const drift = (current - trust) / (i + 1.5);
    trust = Math.max(35, Math.min(99, trust + drift + (rng() - 0.5) * 2.2));
    out.push({
      label: `${points - i}d`,
      trust: Math.round(trust * 10) / 10,
      tasks: Math.round(baseTasks * (0.7 + rng() * 0.6)),
    });
  }
  return out;
}

/** Aggregate a fleet-wide average trend from a set of evaluations. */
export function fleetTrend(evals: Evaluation[], points = 30): TrendPoint[] {
  const scored = evals.filter((e) => e.trust_score !== null);
  if (!scored.length) {
    return Array.from({ length: points }, (_, i) => ({
      label: `${i + 1}d`,
      trust: 0,
      tasks: 0,
    }));
  }
  const perTrend = scored.map((e) =>
    buildTrend(e.id, e.trust_score as number, points),
  );
  return Array.from({ length: points }, (_, i) => ({
    label: `${i + 1}d`,
    trust:
      Math.round(
        (perTrend.reduce((s, t) => s + t[i].trust, 0) / perTrend.length) * 10,
      ) / 10,
    tasks: perTrend.reduce((s, t) => s + t[i].tasks, 0),
  }));
}
