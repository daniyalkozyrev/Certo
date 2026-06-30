"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { motion } from "framer-motion";
import {
  ArrowLeft, Award, Bot, ChevronDown, ClipboardList, Download, FileText, Footprints,
  Gauge, Loader2, ScanSearch, Share2, ShieldCheck, Sparkles, Target, Terminal,
  ThumbsDown, ThumbsUp,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { TrustRing } from "@/components/trust-ring";
import { TrustTrendChart } from "@/components/charts";
import {
  ApiError, getEvaluation, type AgentStep, type EvaluationDetail, type TaskResult,
} from "@/lib/api";
import { CERT_META, buildTrend, certificationFor, scoreTone } from "@/lib/trust";
import { cn } from "@/lib/utils";

const DIS_TONE = { Low: "success", Medium: "warning", High: "danger" } as const;

export default function EvaluationResultPage() {
  const params = useParams<{ id: string }>();
  const [ev, setEv] = useState<EvaluationDetail | null | undefined>(undefined);
  const [error, setError] = useState("");

  // Poll until the run reaches a terminal state — no hard timeout, so a long run
  // (many tasks × judge calls) still updates the UI the moment it finishes.
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function tick() {
      try {
        const data = await getEvaluation(params.id);
        if (!active) return;
        setEv(data);
        if (data.status === "pending" || data.status === "running") {
          timer = setTimeout(tick, 2000);
        }
      } catch (e) {
        if (!active) return;
        if (e instanceof ApiError && e.status === 404) setEv(null);
        else setError(e instanceof ApiError ? e.message : "Failed to load evaluation.");
      }
    }
    tick();
    return () => {
      active = false;
      if (timer) clearTimeout(timer);
    };
  }, [params.id]);

  if (error)
    return <div className="py-20 text-center text-sm text-[hsl(var(--danger))]">{error}</div>;
  if (ev === undefined)
    return (
      <div className="flex items-center justify-center gap-2 py-20 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" /> Loading…
      </div>
    );
  if (ev === null)
    return (
      <div className="mx-auto max-w-md py-20 text-center">
        <p className="font-medium">Evaluation not found</p>
        <Link href="/new" className="mt-4 inline-block"><Button>Run a new evaluation</Button></Link>
      </div>
    );

  if (ev.status === "pending" || ev.status === "running")
    return (
      <div className="mx-auto max-w-md py-20 text-center">
        <Loader2 className="mx-auto size-6 animate-spin text-accent" />
        <p className="mt-3 font-medium">Evaluation {ev.status}…</p>
        <p className="mt-1 text-sm text-muted-foreground">Agent, sandbox and judges are working. This refreshes automatically.</p>
      </div>
    );

  if (ev.status === "failed")
    return (
      <div className="mx-auto max-w-md py-20 text-center">
        <p className="font-medium text-[hsl(var(--danger))]">Evaluation failed</p>
        <p className="mt-1 break-words text-sm text-muted-foreground">{ev.error || "Unknown error."}</p>
        <Link href="/new" className="mt-4 inline-block"><Button>Try again</Button></Link>
      </div>
    );

  // ── completed ──
  const trust = ev.trust_score ?? 0;
  const cert = certificationFor(trust);
  const meta = CERT_META[cert];
  const passRate = ev.pass_rate ?? 0;
  const nTasks = ev.results.length;
  const nPassed = ev.results.filter((r) => (r.reward ?? -1) > 0).length;
  const meanScore =
    nTasks > 0
      ? ev.results.reduce((s, r) => s + (r.judge_score ?? 0), 0) / nTasks
      : 0;
  const judgeNames = Array.from(
    new Set(ev.results.flatMap((r) => (r.judge_votes ?? []).map((v) => v.judge))),
  );

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <Link href="/dashboard" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground">
        <ArrowLeft className="size-4" /> Back to dashboard
      </Link>

      {/* Header */}
      <Card className="overflow-hidden">
        <div className="grid gap-px bg-border md:grid-cols-[1fr_auto]">
          <div className="bg-card p-6">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight">Evaluation report</h1>
              <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1" style={{ color: meta.color, background: `${meta.color}14`, borderColor: `${meta.color}40` }}>
                <span className="size-1.5 rounded-full" style={{ background: meta.color }} />{cert}
              </span>
            </div>
            <p className="mt-1 font-mono text-xs text-muted-foreground">run {ev.id}</p>
            <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm text-muted-foreground">
              <span className="flex items-center gap-1.5"><ScanSearch className="size-4" /> {nPassed}/{nTasks} tasks passed</span>
              <span className="flex items-center gap-1.5"><Sparkles className="size-4" /> {judgeNames.length || 1} judge{judgeNames.length === 1 ? "" : "s"} in ensemble</span>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              <Link href="/new"><Button size="sm"><ScanSearch /> Re-run</Button></Link>
              <Button size="sm" variant="outline" onClick={() => navigator.clipboard?.writeText(`${location.origin}/cert/${ev.id}`)}><Share2 /> Share</Button>
              <Link href={`/cert/${ev.id}`}><Button size="sm" variant="outline"><Download /> Certificate</Button></Link>
            </div>
          </div>
          <div className="flex items-center justify-center bg-card p-6"><TrustRing score={trust} size={158} /></div>
        </div>
      </Card>

      {/* Metrics */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MiniStat icon={ShieldCheck} label="TrustScore" value={trust.toFixed(1)} />
        <MiniStat icon={Target} label="Pass rate" value={`${Math.round(passRate * 100)}%`} />
        <MiniStat icon={Gauge} label="Mean judge score" value={`${meanScore.toFixed(2)}/5`} />
        <MiniStat icon={FileText} label="Tasks" value={String(nTasks)} />
      </div>

      {/* Trend */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Gauge className="size-4" /> TrustScore outlook</CardTitle>
          <CardDescription>Illustrative trend toward the current score — historical runs populate this over time.</CardDescription>
        </CardHeader>
        <CardContent><TrustTrendChart data={buildTrend(ev.id, trust)} height={220} /></CardContent>
      </Card>

      {/* Per-task results */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><FileText className="size-4" /> Task results</CardTitle>
          <CardDescription>Each task: agent output, sandbox execution, ensemble grading and reward signal.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {ev.results.map((r, i) => <TaskRow key={r.id} r={r} index={i} />)}
          {nTasks === 0 && <p className="text-sm text-muted-foreground">No task results recorded.</p>}
        </CardContent>
      </Card>

      {/* Ensemble summary */}
      {judgeNames.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Sparkles className="size-4" /> Ensemble evaluation</CardTitle>
            <CardDescription>Independent judges grade each task; the consensus reduces single-judge subjectivity.</CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto scroll-thin">
              <table className="w-full text-sm">
                <thead className="border-y bg-secondary/40 text-xs uppercase tracking-wider text-muted-foreground">
                  <tr>
                    <th className="px-6 py-3 text-left font-medium">Task</th>
                    {judgeNames.map((j) => <th key={j} className="px-4 py-3 text-center font-medium">{j}</th>)}
                    <th className="px-4 py-3 text-center font-medium">Consensus</th>
                    <th className="px-6 py-3 text-right font-medium">Agreement</th>
                  </tr>
                </thead>
                <tbody>
                  {ev.results.map((r, i) => {
                    const dis = r.disagreement ?? "Low";
                    return (
                      <tr key={r.id} className="border-b last:border-0">
                        <td className="px-6 py-3 font-medium">#{i + 1}</td>
                        {judgeNames.map((j) => {
                          const v = (r.judge_votes ?? []).find((x) => x.judge === j);
                          return <td key={j} className="px-4 py-3 text-center font-mono tabular-nums">{v ? v.score : "—"}</td>;
                        })}
                        <td className="px-4 py-3 text-center font-mono font-semibold tabular-nums">{r.judge_score ?? "—"}</td>
                        <td className="px-6 py-3 text-right">
                          <Badge variant={DIS_TONE[dis]}>{dis === "High" ? "uncertain" : dis}</Badge>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <p className="px-6 py-3 text-xs text-muted-foreground">High disagreement = uncertain case → flag for human review instead of a false-precise score.</p>
          </CardContent>
        </Card>
      )}

      {/* Certificate */}
      <Card className="overflow-hidden">
        <div className="relative p-7" style={{ background: `linear-gradient(135deg, ${meta.color}14, transparent 70%)` }}>
          <div className="pointer-events-none absolute inset-0 grid-bg opacity-[0.12]" />
          <div className="relative flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Certo Certificate of Trust</p>
              <h3 className="mt-2 text-xl font-semibold">Evaluation {ev.id.slice(0, 8)}</h3>
              <p className="mt-3 text-3xl font-semibold" style={{ color: meta.color }}>{cert}</p>
              <p className="text-xs text-muted-foreground">{meta.blurb}</p>
            </div>
            <TrustRing score={trust} size={130} />
          </div>
          <div className="relative mt-6 flex flex-wrap items-center justify-between gap-3 border-t pt-5">
            <div className="text-xs text-muted-foreground">Certificate No. <span className="font-mono text-foreground">CERTO-2026-{ev.id.slice(0, 8).toUpperCase()}</span></div>
            <Link href={`/cert/${ev.id}`}><Button size="sm"><Download /> Open certificate</Button></Link>
          </div>
        </div>
      </Card>

      <div className="flex items-center justify-center gap-2 pb-6">
        <Link href="/new"><Button variant="outline"><ScanSearch /> Evaluate another agent</Button></Link>
        <Link href="/dashboard"><Button variant="ghost"><Award /> View all runs</Button></Link>
      </div>
    </div>
  );
}

function MiniStat({ icon: Icon, label, value }: { icon: React.ComponentType<{ className?: string }>; label: string; value: string }) {
  return (
    <Card className="p-5">
      <div className="flex items-center gap-2 text-sm text-muted-foreground"><Icon className="size-4" />{label}</div>
      <p className="mt-2 text-2xl font-semibold tabular-nums">{value}</p>
    </Card>
  );
}

function TaskRow({ r, index }: { r: TaskResult; index: number }) {
  const [open, setOpen] = useState(false);
  const passed = (r.reward ?? -1) > 0;
  const tone = scoreTone(((r.judge_score ?? 1) / 5) * 100);
  return (
    <div className="rounded-lg border">
      <button onClick={() => setOpen((o) => !o)} className="flex w-full items-center gap-3 p-4 text-left">
        <Badge variant={passed ? "success" : "danger"}>
          {passed ? <ThumbsUp className="size-3" /> : <ThumbsDown className="size-3" />} {passed ? "+1" : "−1"}
        </Badge>
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium">Task #{index + 1}</p>
          <p className="truncate text-xs text-muted-foreground">
            judge {r.judge_score ?? "—"}/5
            {r.disagreement ? ` · ${r.disagreement} agreement` : ""}
            {r.step_count ? ` · ${r.step_count} steps`
              + (r.mean_step_score != null ? ` (avg ${r.mean_step_score.toFixed(1)}/5)` : "")
              : r.sandbox_exit_code !== null ? ` · exit ${r.sandbox_exit_code}` : ""}
          </p>
        </div>
        <span className={cn("font-mono text-sm font-semibold tabular-nums",
          tone === "success" ? "text-[hsl(var(--success))]" : tone === "warning" ? "text-[hsl(var(--warning))]" : "text-[hsl(var(--danger))]")}>
          {r.judge_score ?? "—"}
        </span>
        <ChevronDown className={cn("size-4 shrink-0 text-muted-foreground transition-transform", open && "rotate-180")} />
      </button>
      {open && (
        <div className="space-y-3 border-t bg-secondary/30 p-4 text-sm">
          {r.steps && r.steps.length > 0 && <Trajectory steps={r.steps} />}
          {r.agent_output && (
            <Block label={r.steps?.length ? "Final answer" : "Agent output"}>{r.agent_output}</Block>
          )}
          {(r.sandbox_stdout || r.sandbox_stderr) && (
            <div>
              <p className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground"><Terminal className="size-3" /> Sandbox</p>
              <div className="space-y-1 rounded-lg border bg-background p-3 font-mono text-xs">
                {r.sandbox_stdout && <p className="whitespace-pre-wrap"><span className="text-accent">stdout →</span> {r.sandbox_stdout}</p>}
                {r.sandbox_stderr && <p className="whitespace-pre-wrap"><span className="text-[hsl(var(--danger))]">stderr →</span> {r.sandbox_stderr}</p>}
              </div>
            </div>
          )}
          {r.judge_votes && r.judge_votes.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Judge votes</p>
              <div className="space-y-2">
                {r.judge_votes.map((v) => (
                  <div key={v.judge} className="rounded-lg border bg-background p-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{v.judge}</span>
                      <span className="font-mono text-sm tabular-nums">{v.score}/5</span>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">{v.feedback}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
          {r.judge_feedback && !r.judge_votes?.length && <Block label="Judge feedback">{r.judge_feedback}</Block>}
        </div>
      )}
    </div>
  );
}

function Block({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">{label}</p>
      <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg border bg-background p-3 font-mono text-xs scroll-thin">{children}</pre>
    </div>
  );
}

const ROLE_ICON: Record<string, React.ComponentType<{ className?: string }>> = {
  planner: ClipboardList,
  reviewer: ShieldCheck,
  worker: Bot,
  agent: Bot,
};

function stepScoreTone(score: number | null) {
  if (score == null) return "text-muted-foreground";
  if (score >= 4) return "text-[hsl(var(--success))]";
  if (score >= 3) return "text-[hsl(var(--warning))]";
  return "text-[hsl(var(--danger))]";
}

function Trajectory({ steps }: { steps: AgentStep[] }) {
  return (
    <div>
      <p className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        <Footprints className="size-3" /> Agent trajectory · judged step by step
      </p>
      <div className="space-y-2">
        {steps.map((s) => <StepCard key={s.id} s={s} />)}
      </div>
    </div>
  );
}

function StepCard({ s }: { s: AgentStep }) {
  const Icon = ROLE_ICON[s.role] ?? Bot;
  return (
    <div className="rounded-lg border bg-background">
      <div className="flex items-center gap-2 border-b px-3 py-2">
        <Icon className="size-3.5 text-accent" />
        <span className="text-xs font-medium">Step {s.step_index}</span>
        <Badge variant="outline" className="text-[10px] uppercase">{s.role}</Badge>
        <span className={cn("ml-auto font-mono text-xs font-semibold tabular-nums", stepScoreTone(s.judge_score))}>
          {s.judge_score != null ? `${s.judge_score}/5` : "—"}
        </span>
      </div>
      <div className="space-y-2 p-3 text-xs">
        {s.thought && <p className="whitespace-pre-wrap text-muted-foreground"><span className="font-semibold text-foreground">thought: </span>{s.thought}</p>}
        {s.action_code && (
          <pre className="overflow-x-auto whitespace-pre-wrap rounded-md border bg-secondary/40 p-2 font-mono scroll-thin">{s.action_code}</pre>
        )}
        {(s.observation_stdout?.trim() || s.observation_stderr?.trim()) && (
          <div className="rounded-md border bg-secondary/40 p-2 font-mono">
            {s.observation_stdout?.trim() && <p className="whitespace-pre-wrap"><span className="text-accent">stdout →</span> {s.observation_stdout.trim()}</p>}
            {s.observation_stderr?.trim() && <p className="whitespace-pre-wrap"><span className="text-[hsl(var(--danger))]">stderr →</span> {s.observation_stderr.trim()}</p>}
          </div>
        )}
        {s.judge_feedback && (
          <p className="border-l-2 border-accent/40 pl-2 text-muted-foreground"><span className="font-semibold text-foreground">judge: </span>{s.judge_feedback}</p>
        )}
      </div>
    </div>
  );
}
