"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Activity, Bell, Gauge, ShieldCheck, Target } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrustTrendChart, TaskVolumeChart } from "@/components/charts";
import {
  ApiError, getEvaluation, listAgents, listEvaluations,
  type Agent, type Evaluation, type EvaluationDetail,
} from "@/lib/api";
import { buildTrend, statusFromScore, STATUS_TONE } from "@/lib/trust";
import { cn } from "@/lib/utils";

export default function MonitoringPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [evals, setEvals] = useState<Evaluation[]>([]);
  const [agentId, setAgentId] = useState("");
  const [detail, setDetail] = useState<EvaluationDetail | null>(null);
  const [error, setError] = useState("");
  const [ready, setReady] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [a, e] = await Promise.all([listAgents(), listEvaluations()]);
        setAgents(a.items);
        setEvals(e.items);
        const firstWithRun = a.items.find((ag) => e.items.some((ev) => ev.agent_id === ag.id));
        if (firstWithRun) setAgentId(firstWithRun.id);
        else if (a.items[0]) setAgentId(a.items[0].id);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load.");
      } finally {
        setReady(true);
      }
    })();
  }, []);

  const agentEvals = useMemo(
    () => evals.filter((e) => e.agent_id === agentId && e.status === "completed")
      .sort((a, b) => +new Date(b.created_at) - +new Date(a.created_at)),
    [evals, agentId],
  );
  const latest = agentEvals[0];

  useEffect(() => {
    setDetail(null);
    if (!latest) return;
    getEvaluation(latest.id).then(setDetail).catch(() => setDetail(null));
  }, [latest]);

  const agent = agents.find((a) => a.id === agentId);

  if (!ready) return <div className="py-20 text-center text-sm text-muted-foreground">Loading…</div>;
  if (error) return <div className="py-20 text-center text-sm text-[hsl(var(--danger))]">{error}</div>;
  if (!agents.length)
    return (
      <div className="py-20 text-center">
        <p className="font-medium">No agents to monitor</p>
        <Link href="/new" className="mt-3 inline-block text-sm font-medium text-accent hover:underline">Run an evaluation →</Link>
      </div>
    );

  const trust = latest?.trust_score ?? 0;
  const st = statusFromScore(latest?.trust_score ?? null, latest?.pass_rate ?? null);
  const trend = latest ? buildTrend(latest.id, trust) : [];
  const failing = (detail?.results ?? []).filter((r) => (r.reward ?? -1) < 0 || r.disagreement === "High");

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div><h1 className="text-2xl font-semibold tracking-tight">Monitoring</h1><p className="mt-1 text-sm text-muted-foreground">Per-agent TrustScore, pass rate and flagged tasks.</p></div>
        <select value={agentId} onChange={(e) => setAgentId(e.target.value)} className="rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring">
          {agents.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-lg font-semibold">{agent?.name}</h2>
        {latest ? (
          <>
            <Badge variant={STATUS_TONE[st]}><Activity className="size-3" /> {st}</Badge>
            <span className="text-sm text-muted-foreground">{agentEvals.length} completed run{agentEvals.length === 1 ? "" : "s"}</span>
            <Link href={`/audit/${latest.id}`} className="ml-auto text-xs font-medium text-accent hover:underline">View latest run →</Link>
          </>
        ) : (
          <span className="text-sm text-muted-foreground">No completed runs yet.</span>
        )}
      </div>

      {latest ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Kpi icon={ShieldCheck} label="TrustScore" value={trust.toFixed(1)} />
            <Kpi icon={Target} label="Pass rate" value={`${Math.round((latest.pass_rate ?? 0) * 100)}%`} />
            <Kpi icon={Gauge} label="Tasks" value={String(detail?.results.length ?? "—")} />
            <Kpi icon={Bell} label="Flagged" value={String(failing.length)} good={failing.length === 0} />
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader><CardTitle>TrustScore — outlook</CardTitle><CardDescription>Illustrative trend toward the latest score</CardDescription></CardHeader>
              <CardContent><TrustTrendChart data={trend} height={260} /></CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2"><Bell className="size-4 text-[hsl(var(--warning))]" /> Flagged tasks</CardTitle><CardDescription>Failed or high-disagreement</CardDescription></CardHeader>
              <CardContent className="space-y-2 text-sm">
                {failing.length === 0 && <p className="text-muted-foreground">No flagged tasks. 🎉</p>}
                {failing.slice(0, 6).map((r, i) => (
                  <div key={r.id} className="flex items-center justify-between rounded-lg border p-3">
                    <span className="min-w-0 truncate">Task #{i + 1} · judge {r.judge_score ?? "—"}/5</span>
                    <Badge variant={r.disagreement === "High" ? "warning" : "danger"}>{r.disagreement === "High" ? "uncertain" : "failed"}</Badge>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader><CardTitle>Task volume</CardTitle><CardDescription>Illustrative daily tasks</CardDescription></CardHeader>
            <CardContent><TaskVolumeChart data={trend} height={220} /></CardContent>
          </Card>
        </>
      ) : (
        <Card><CardContent className="py-16 text-center text-sm text-muted-foreground">Run an evaluation for this agent to see monitoring data.</CardContent></Card>
      )}
    </div>
  );
}

function Kpi({ icon: Icon, label, value, good }: { icon: React.ComponentType<{ className?: string }>; label: string; value: string; good?: boolean }) {
  return (
    <Card className="p-5">
      <div className="flex items-center gap-2 text-sm text-muted-foreground"><Icon className="size-4" />{label}</div>
      <p className={cn("mt-2 text-2xl font-semibold tabular-nums", good && "text-[hsl(var(--success))]")}>{value}</p>
    </Card>
  );
}
