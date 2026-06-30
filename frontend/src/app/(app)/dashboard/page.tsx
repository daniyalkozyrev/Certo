"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Activity, AlertTriangle, Bot, Plus, ShieldCheck, TrendingUp,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { TrustTrendChart, TaskVolumeChart } from "@/components/charts";
import { AnimatedNumber } from "@/components/animated-number";
import { ApiError, listAgents, listEvaluations, type Agent, type Evaluation } from "@/lib/api";
import {
  CERT_META, certificationFor, fleetTrend, scoreTone, statusFromScore, STATUS_TONE,
} from "@/lib/trust";
import { cn, formatRelativeTime } from "@/lib/utils";

export default function OverviewPage() {
  const [evals, setEvals] = useState<Evaluation[] | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [e, a] = await Promise.all([listEvaluations(), listAgents()]);
        setEvals(e.items);
        setAgents(a.items);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load.");
        setEvals([]);
      }
    })();
  }, []);

  const agentName = useMemo(() => {
    const m = new Map(agents.map((a) => [a.id, a.name]));
    return (id: string) => m.get(id) ?? `${id.slice(0, 8)}…`;
  }, [agents]);

  const completed = useMemo(
    () => (evals ?? []).filter((e) => e.status === "completed" && e.trust_score !== null),
    [evals],
  );

  const stats = useMemo(() => {
    if (!completed.length) return null;
    const avg = completed.reduce((s, e) => s + (e.trust_score ?? 0), 0) / completed.length;
    const avgPass = completed.reduce((s, e) => s + (e.pass_rate ?? 0), 0) / completed.length;
    const atRisk = completed.filter(
      (e) => statusFromScore(e.trust_score, e.pass_rate) === "At Risk" ||
        statusFromScore(e.trust_score, e.pass_rate) === "Degraded",
    );
    return { avg, avgPass, atRisk, trend: fleetTrend(completed) };
  }, [completed]);

  const recent = useMemo(
    () => [...(evals ?? [])].sort((a, b) => +new Date(b.created_at) - +new Date(a.created_at)).slice(0, 6),
    [evals],
  );
  const top = useMemo(
    () => [...completed].sort((a, b) => (b.trust_score ?? 0) - (a.trust_score ?? 0)).slice(0, 5),
    [completed],
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Overview</h1>
          <p className="mt-1 text-sm text-muted-foreground">TrustScore & evaluation posture across your AI agents.</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="success"><Activity className="size-3" /> Connected to backend</Badge>
          <Link href="/new"><Button><Plus /> New evaluation</Button></Link>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-[hsl(var(--danger))]/30 bg-[hsl(var(--danger))]/5 p-4 text-sm">
          <p className="font-medium text-[hsl(var(--danger))]">Backend unreachable</p>
          <p className="mt-1 text-muted-foreground">{error}</p>
        </div>
      )}

      {evals === null && (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 4 }).map((_, i) => <div key={i} className="skeleton h-28 rounded-xl" />)}</div>
          <div className="grid gap-6 lg:grid-cols-3"><div className="skeleton h-72 rounded-xl lg:col-span-2" /><div className="skeleton h-72 rounded-xl" /></div>
        </div>
      )}

      {evals !== null && !stats && !error && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
            <ShieldCheck className="size-8 text-muted-foreground" />
            <p className="font-medium">No completed evaluations yet</p>
            <p className="max-w-sm text-sm text-muted-foreground">Run your first evaluation to populate the dashboard with a real TrustScore.</p>
            <Link href="/new"><Button><Plus /> Run an evaluation</Button></Link>
          </CardContent>
        </Card>
      )}

      {stats && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Kpi icon={Bot} label="Agents" value={<AnimatedNumber value={agents.length} />} delta={`${(evals ?? []).length} runs total`} />
            <Kpi icon={ShieldCheck} label="Avg TrustScore" value={<AnimatedNumber value={stats.avg} decimals={1} />} delta={`${completed.length} completed`} />
            <Kpi icon={TrendingUp} label="Avg pass rate" value={`${Math.round(stats.avgPass * 100)}%`} delta="across completed runs" />
            <Kpi icon={AlertTriangle} label="Need attention" value={<AnimatedNumber value={stats.atRisk.length} />} delta={stats.atRisk.length ? "below target" : "all healthy"} tone={stats.atRisk.length ? "danger" : "default"} />
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader><CardTitle>TrustScore trend</CardTitle><CardDescription>Fleet-wide average (illustrative)</CardDescription></CardHeader>
              <CardContent><TrustTrendChart data={stats.trend} height={260} /></CardContent>
            </Card>
            <Card>
              <CardHeader className="flex-row items-center justify-between">
                <div><CardTitle>Top runs</CardTitle><CardDescription>By TrustScore</CardDescription></div>
                <Link href="/agents" className="text-xs font-medium text-accent hover:underline">Agents</Link>
              </CardHeader>
              <CardContent className="space-y-1">
                {top.map((e, i) => (
                  <Link key={e.id} href={`/audit/${e.id}`} className="flex items-center gap-3 rounded-lg px-2 py-2 transition-colors hover:bg-secondary/60">
                    <span className="w-4 text-center font-mono text-sm text-muted-foreground">{i + 1}</span>
                    <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{agentName(e.agent_id)}</p><p className="truncate text-xs text-muted-foreground">{certificationFor(e.trust_score ?? 0)}</p></div>
                    <ScoreText score={e.trust_score ?? 0} />
                  </Link>
                ))}
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader><CardTitle>Task volume</CardTitle><CardDescription>Tasks evaluated across the fleet (illustrative)</CardDescription></CardHeader>
              <CardContent><TaskVolumeChart data={stats.trend} height={240} /></CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2"><AlertTriangle className="size-4 text-[hsl(var(--warning))]" /> Attention</CardTitle><CardDescription>Runs below target</CardDescription></CardHeader>
              <CardContent className="space-y-2">
                {stats.atRisk.length === 0 && <p className="text-sm text-muted-foreground">All runs healthy. 🎉</p>}
                {stats.atRisk.slice(0, 4).map((e) => {
                  const st = statusFromScore(e.trust_score, e.pass_rate);
                  return (
                    <Link key={e.id} href={`/audit/${e.id}`} className="flex items-center justify-between rounded-lg border p-3 transition-colors hover:bg-secondary/40">
                      <div className="min-w-0"><p className="truncate text-sm font-medium">{agentName(e.agent_id)}</p><p className="text-xs text-muted-foreground">TrustScore {(e.trust_score ?? 0).toFixed(0)}</p></div>
                      <Badge variant={STATUS_TONE[st]}>{st}</Badge>
                    </Link>
                  );
                })}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <div><CardTitle>Recent evaluations</CardTitle><CardDescription>Latest runs</CardDescription></div>
              <Link href="/new" className="text-xs font-medium text-accent hover:underline">New run</Link>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto scroll-thin">
                <table className="w-full text-sm">
                  <thead className="border-y bg-secondary/40 text-xs uppercase tracking-wider text-muted-foreground">
                    <tr><th className="px-6 py-3 text-left font-medium">Agent</th><th className="px-6 py-3 text-left font-medium">Status</th><th className="px-6 py-3 text-right font-medium">Trust</th><th className="px-6 py-3 text-left font-medium">Cert</th><th className="px-6 py-3 text-right font-medium">When</th></tr>
                  </thead>
                  <tbody>
                    {recent.map((e) => {
                      const score = e.trust_score ?? 0;
                      const cert = certificationFor(score);
                      const meta = CERT_META[cert];
                      return (
                        <tr key={e.id} className="border-b last:border-0 transition-colors hover:bg-secondary/30">
                          <td className="px-6 py-3"><Link href={`/audit/${e.id}`} className="font-medium hover:text-accent">{agentName(e.agent_id)}</Link></td>
                          <td className="px-6 py-3"><StatusBadge status={e.status} /></td>
                          <td className="px-6 py-3 text-right">{e.trust_score !== null ? <ScoreText score={score} /> : <span className="text-muted-foreground">—</span>}</td>
                          <td className="px-6 py-3">{e.trust_score !== null ? <span className="inline-flex items-center gap-1.5 text-xs font-medium" style={{ color: meta.color }}><ShieldCheck className="size-3" />{cert}</span> : <span className="text-xs text-muted-foreground">—</span>}</td>
                          <td className="px-6 py-3 text-right text-xs text-muted-foreground">{formatRelativeTime(e.created_at)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: Evaluation["status"] }) {
  const map = {
    completed: "success", running: "accent", pending: "warning", failed: "danger",
  } as const;
  return <Badge variant={map[status]}>{status}</Badge>;
}

function Kpi({ icon: Icon, label, value, delta, tone = "default" }: { icon: React.ComponentType<{ className?: string }>; label: string; value: React.ReactNode; delta?: string; tone?: "default" | "danger" }) {
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
      <Card className="p-5">
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">{label}</p>
          <span className="grid size-8 place-items-center rounded-lg bg-secondary text-muted-foreground"><Icon className="size-4" /></span>
        </div>
        <p className="mt-3 text-3xl font-semibold tracking-tight tabular-nums">{value}</p>
        {delta && <p className={cn("mt-1.5 text-xs", tone === "danger" ? "text-[hsl(var(--danger))]" : "text-muted-foreground")}>{delta}</p>}
      </Card>
    </motion.div>
  );
}

function ScoreText({ score }: { score: number }) {
  const tone = scoreTone(score);
  const c = tone === "success" ? "text-[hsl(var(--success))]" : tone === "warning" ? "text-[hsl(var(--warning))]" : "text-[hsl(var(--danger))]";
  return <span className={cn("font-mono font-semibold tabular-nums", c)}>{score.toFixed(0)}</span>;
}
