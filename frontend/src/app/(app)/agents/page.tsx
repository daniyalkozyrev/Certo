"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Bot, Loader2, Plus, Search, X } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { MiniSparkline } from "@/components/charts";
import {
  ApiError, createAgent, listAgents, listEvaluations, type Agent, type Evaluation,
} from "@/lib/api";
import {
  buildTrend, certificationFor, CERT_META, scoreTone, statusFromScore, STATUS_TONE,
} from "@/lib/trust";
import { cn, formatRelativeTime } from "@/lib/utils";

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[] | null>(null);
  const [evals, setEvals] = useState<Evaluation[]>([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  async function refresh() {
    try {
      const [a, e] = await Promise.all([listAgents(), listEvaluations()]);
      setAgents(a.items);
      setEvals(e.items);
      setError("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load agents.");
      setAgents([]);
    }
  }

  useEffect(() => {
    refresh();
    // Pick up ?q= from the topbar search (read from URL to avoid a Suspense boundary).
    const q = new URLSearchParams(window.location.search).get("q");
    if (q) setQuery(q);
  }, []);

  // latest completed evaluation per agent
  const latestByAgent = useMemo(() => {
    const m = new Map<string, Evaluation>();
    for (const e of [...evals].sort((a, b) => +new Date(a.created_at) - +new Date(b.created_at))) {
      if (e.status === "completed") m.set(e.agent_id, e);
    }
    return m;
  }, [evals]);

  const filtered = useMemo(
    () => (agents ?? []).filter((a) => query === "" || a.name.toLowerCase().includes(query.toLowerCase())),
    [agents, query],
  );

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div><h1 className="text-2xl font-semibold tracking-tight">Agents</h1><p className="mt-1 text-sm text-muted-foreground">Every registered AI agent, scored by its latest evaluation.</p></div>
        <Button onClick={() => setShowCreate(true)}><Plus /> New agent</Button>
      </div>

      <div className="flex w-full items-center gap-2 rounded-lg border bg-background px-3 py-2 text-sm lg:max-w-xs">
        <Search className="size-4 text-muted-foreground" />
        <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search agents…" className="w-full bg-transparent outline-none placeholder:text-muted-foreground" />
      </div>

      {error && <p className="text-sm text-[hsl(var(--danger))]">{error}</p>}

      {agents === null ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 6 }).map((_, i) => <div key={i} className="skeleton h-40 rounded-xl" />)}</div>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-16 text-center">
            <Bot className="size-8 text-muted-foreground" />
            <p className="font-medium">No agents yet</p>
            <p className="max-w-sm text-sm text-muted-foreground">Register an agent, then run an evaluation to score it.</p>
            <Button onClick={() => setShowCreate(true)}><Plus /> Create agent</Button>
          </CardContent>
        </Card>
      ) : (
        <>
          <p className="text-xs text-muted-foreground">{filtered.length} of {agents.length} agents</p>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {filtered.map((a) => {
              const ev = latestByAgent.get(a.id);
              const score = ev?.trust_score ?? null;
              const cert = score !== null ? certificationFor(score) : null;
              const meta = cert ? CERT_META[cert] : null;
              const st = statusFromScore(score, ev?.pass_rate ?? null);
              return (
                <Card key={a.id} className="group h-full">
                  <CardContent className="p-5">
                    <div className="flex items-start justify-between">
                      <div className="min-w-0">
                        <p className="truncate font-semibold">{a.name}</p>
                        <p className="truncate text-xs text-muted-foreground">{a.config?.model ? String(a.config.model) : "mock agent"} · {formatRelativeTime(a.created_at)}</p>
                      </div>
                      {meta && cert && (
                        <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium ring-1" style={{ color: meta.color, background: `${meta.color}14`, borderColor: `${meta.color}40` }}><span className="size-1.5 rounded-full" style={{ background: meta.color }} />{cert}</span>
                      )}
                    </div>
                    <div className="my-3 h-9">
                      {score !== null ? <MiniSparkline data={buildTrend(ev!.id, score)} /> : <div className="flex h-full items-center text-xs text-muted-foreground">no evaluation yet</div>}
                    </div>
                    <div className="flex items-end justify-between">
                      <div>
                        <p className="text-[11px] uppercase tracking-wider text-muted-foreground">Trust</p>
                        {score !== null ? <ScoreText score={score} /> : <span className="text-muted-foreground">—</span>}
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        {score !== null && <Badge variant={STATUS_TONE[st]}>{st}</Badge>}
                        {ev ? (
                          <Link href={`/audit/${ev.id}`} className="text-xs font-medium text-accent hover:underline">View run →</Link>
                        ) : (
                          <Link href="/new" className="text-xs font-medium text-accent hover:underline">Evaluate →</Link>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </>
      )}

      {showCreate && <CreateAgentModal onClose={() => setShowCreate(false)} onCreated={() => { setShowCreate(false); refresh(); }} />}
    </div>
  );
}

function ScoreText({ score }: { score: number }) {
  const tone = scoreTone(score);
  const c = tone === "success" ? "text-[hsl(var(--success))]" : tone === "warning" ? "text-[hsl(var(--warning))]" : "text-[hsl(var(--danger))]";
  return <span className={cn("text-2xl font-mono font-semibold tabular-nums", c)}>{score.toFixed(0)}</span>;
}

function CreateAgentModal({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [name, setName] = useState("");
  const [model, setModel] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit() {
    if (!name.trim()) { setError("Name is required."); return; }
    setBusy(true); setError("");
    try {
      await createAgent({
        name: name.trim(),
        config: {
          model: model || null,
          base_url: baseUrl || null,
          api_key: apiKey || null,
          system_prompt: systemPrompt || null,
        },
      });
      onCreated();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to create agent.");
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4" onClick={onClose}>
      <Card className="w-full max-w-md" onClick={(e) => e.stopPropagation()}>
        <CardContent className="space-y-4 pt-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">New agent</h2>
            <button onClick={onClose} aria-label="Close" className="text-muted-foreground hover:text-foreground"><X className="size-4" /></button>
          </div>
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Agent name *" className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
          <input value={model} onChange={(e) => setModel(e.target.value)} placeholder="Model (optional)" className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
          <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="Base URL (optional)" className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
          <input value={apiKey} onChange={(e) => setApiKey(e.target.value)} type="password" placeholder="API key (optional — empty = mock)" className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
          <textarea value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)} rows={2} placeholder="System prompt (optional)" className="w-full resize-none rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
          {error && <p className="text-sm text-[hsl(var(--danger))]">{error}</p>}
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={onClose}>Cancel</Button>
            <Button onClick={submit} disabled={busy}>{busy ? <Loader2 className="size-4 animate-spin" /> : <Plus className="size-4" />} Create</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
