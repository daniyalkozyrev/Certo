"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft, Bot, ClipboardList, Footprints, Loader2, ShieldCheck, Wrench,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { TrustRing } from "@/components/trust-ring";
import { ApiError, getTrace, pollTrace, type Span, type TraceDetail } from "@/lib/api";
import { CERT_META, certificationFor } from "@/lib/trust";
import { cn } from "@/lib/utils";

const ROLE_ICON: Record<string, React.ComponentType<{ className?: string }>> = {
  agent: Bot, tool: Wrench, llm: ClipboardList, observation: Footprints, handoff: ArrowLeft,
};

function fmt(v: unknown): string {
  if (v == null) return "";
  return typeof v === "string" ? v : JSON.stringify(v, null, 2);
}

function tone(score: number | null) {
  if (score == null) return "text-muted-foreground";
  if (score >= 4) return "text-[hsl(var(--success))]";
  if (score >= 3) return "text-[hsl(var(--warning))]";
  return "text-[hsl(var(--danger))]";
}

export default function TraceDetailPage() {
  const params = useParams<{ id: string }>();
  const [t, setT] = useState<TraceDetail | null | undefined>(undefined);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const first = await getTrace(params.id);
      setT(first);
      if (first.status === "running") setT(await pollTrace(params.id));
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) setT(null);
      else setError(e instanceof ApiError ? e.message : "Failed to load trace.");
    }
  }, [params.id]);

  useEffect(() => {
    load();
  }, [load]);

  if (error) return <div className="py-20 text-center text-sm text-[hsl(var(--danger))]">{error}</div>;
  if (t === undefined)
    return (
      <div className="flex items-center justify-center gap-2 py-20 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" /> Loading…
      </div>
    );
  if (t === null)
    return (
      <div className="mx-auto max-w-md py-20 text-center">
        <p className="font-medium">Trace not found</p>
        <Link href="/traces" className="mt-4 inline-block"><Button>Back to traces</Button></Link>
      </div>
    );
  if (t.status === "running")
    return (
      <div className="mx-auto max-w-md py-20 text-center">
        <Loader2 className="mx-auto size-6 animate-spin text-accent" />
        <p className="mt-3 font-medium">Scoring trajectory…</p>
        <p className="mt-1 text-sm text-muted-foreground">The judge is grading each span. This refreshes automatically.</p>
      </div>
    );

  const trust = t.trust_score ?? 0;
  const cert = certificationFor(trust);
  const meta = CERT_META[cert];
  const s = t.summary ?? {};
  const num = (k: string) => (typeof s[k] === "number" ? (s[k] as number) : null);

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <Link href="/traces" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground">
        <ArrowLeft className="size-4" /> Back to traces
      </Link>

      {/* Header */}
      <Card className="overflow-hidden">
        <div className="grid gap-px bg-border md:grid-cols-[1fr_auto]">
          <div className="bg-card p-6">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-2xl font-semibold tracking-tight">{t.name || "Trace report"}</h1>
              <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1" style={{ color: meta.color, background: `${meta.color}14`, borderColor: `${meta.color}40` }}>
                <span className="size-1.5 rounded-full" style={{ background: meta.color }} />{cert}
              </span>
              <Badge variant="outline">{t.source}</Badge>
              {s.is_multi_agent ? <Badge variant="accent">multi-agent</Badge> : null}
            </div>
            {t.task && <p className="mt-2 text-sm text-muted-foreground">{t.task}</p>}
            <p className="mt-2 font-mono text-xs text-muted-foreground">trace {t.id}</p>
          </div>
          <div className="flex items-center justify-center bg-card p-6"><TrustRing score={trust} size={150} /></div>
        </div>
      </Card>

      {/* Axes */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MiniStat icon={ShieldCheck} label="TrustScore" value={trust.toFixed(1)} />
        <MiniStat icon={Footprints} label="Spans" value={String(num("n_spans") ?? t.spans.length)} />
        <MiniStat icon={ClipboardList} label="Mean step" value={num("mean_step_score") != null ? `${num("mean_step_score")!.toFixed(1)}/5` : "—"} />
        <MiniStat icon={ShieldCheck} label="Outcome" value={s.outcome_passed == null ? "—" : s.outcome_passed ? "passed" : "failed"} />
      </div>

      {/* Spans */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Footprints className="size-4" /> Trajectory · judged step by step</CardTitle>
          <CardDescription>Every span the agent emitted, graded individually by the judge.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {t.spans.map((sp) => <SpanCard key={sp.id} s={sp} />)}
          {t.spans.length === 0 && <p className="text-sm text-muted-foreground">No spans recorded.</p>}
        </CardContent>
      </Card>

      {/* Final answer + verdict */}
      {(t.final_output || typeof s.final_feedback === "string") && (
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><ShieldCheck className="size-4" /> Final verdict</CardTitle></CardHeader>
          <CardContent className="space-y-3 text-sm">
            {t.final_output && (
              <div>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Final output</p>
                <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg border bg-background p-3 font-mono text-xs scroll-thin">{t.final_output}</pre>
              </div>
            )}
            {typeof s.final_feedback === "string" && (
              <p className="border-l-2 border-accent/40 pl-3 text-muted-foreground">{s.final_feedback}</p>
            )}
          </CardContent>
        </Card>
      )}
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

function SpanCard({ s }: { s: Span }) {
  const Icon = ROLE_ICON[s.kind] ?? Wrench;
  const input = fmt(s.input);
  const output = fmt(s.output);
  return (
    <div className="rounded-lg border bg-background">
      <div className="flex items-center gap-2 border-b px-3 py-2">
        <Icon className="size-3.5 text-accent" />
        <span className="text-xs font-medium">Span {s.step_index}</span>
        <Badge variant="outline" className="text-[10px] uppercase">{s.kind}{s.name ? `: ${s.name}` : ""}</Badge>
        <span className={cn("ml-auto font-mono text-xs font-semibold tabular-nums", tone(s.judge_score))}>
          {s.judge_score != null ? `${s.judge_score}/5` : "—"}
        </span>
      </div>
      <div className="space-y-2 p-3 text-xs">
        {input && <Block label="input">{input}</Block>}
        {output && <Block label="output">{output}</Block>}
        {s.error && <Block label="error">{s.error}</Block>}
        {s.judge_feedback && (
          <p className="border-l-2 border-accent/40 pl-2 text-muted-foreground"><span className="font-semibold text-foreground">judge: </span>{s.judge_feedback}</p>
        )}
      </div>
    </div>
  );
}

function Block({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="mb-1 font-semibold uppercase tracking-wider text-muted-foreground">{label}</p>
      <pre className="overflow-x-auto whitespace-pre-wrap rounded-md border bg-secondary/40 p-2 font-mono scroll-thin">{children}</pre>
    </div>
  );
}
