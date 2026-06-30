"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle2, Loader2, Play, ShieldCheck, Boxes, Sparkles, Plus, Database,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  ApiError,
  createAgent,
  createDemoBenchmark,
  createEvaluation,
  listAgents,
  listBenchmarks,
  pollEvaluation,
  type Agent,
  type AgentType,
  type Benchmark,
} from "@/lib/api";

const STEPS = [
  "Creating evaluation run",
  "Agent working in the live E2B sandbox (step by step)",
  "Judge grading every agent step",
  "Final holistic grade + deterministic test checks",
  "Aggregating reward signals & TrustScore",
];

const AGENT_TYPES: { value: AgentType; label: string; hint: string }[] = [
  { value: "llm_endpoint", label: "One-shot", hint: "Writes one program, runs once." },
  { value: "agentic", label: "Agentic (loop)", hint: "Lives in the sandbox: think → run → observe → repeat." },
  { value: "multi_agent", label: "Multi-agent", hint: "Planner → Worker(loop) → Reviewer. Each step judged." },
];

export default function NewEvaluationPage() {
  const router = useRouter();

  const [agents, setAgents] = useState<Agent[]>([]);
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([]);
  const [loading, setLoading] = useState(true);

  const [agentMode, setAgentMode] = useState<"existing" | "new">("existing");
  const [agentId, setAgentId] = useState("");
  const [benchmarkId, setBenchmarkId] = useState("");

  // new-agent fields
  const [name, setName] = useState("");
  const [agentType, setAgentType] = useState<AgentType>("llm_endpoint");
  const [model, setModel] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [systemPrompt, setSystemPrompt] = useState("");

  const [phase, setPhase] = useState<"form" | "running">("form");
  const [step, setStep] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      const [a, b] = await Promise.all([listAgents(), listBenchmarks()]);
      setAgents(a.items);
      setBenchmarks(b.items);
      setAgentMode(a.items.length ? "existing" : "new");
      if (a.items[0]) setAgentId(a.items[0].id);
      if (b.items[0]) setBenchmarkId(b.items[0].id);
      setError("");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load data.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  // advance the visual pipeline while the request runs
  useEffect(() => {
    if (phase !== "running") return;
    if (step >= STEPS.length - 1) return;
    const t = setTimeout(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 700);
    return () => clearTimeout(t);
  }, [phase, step]);

  async function makeDemoBenchmark() {
    setBusy(true);
    setError("");
    try {
      const b = await createDemoBenchmark();
      setBenchmarks((prev) => [b, ...prev]);
      setBenchmarkId(b.id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to create benchmark.");
    } finally {
      setBusy(false);
    }
  }

  async function run() {
    setError("");
    if (!benchmarkId) {
      setError("Select or create a benchmark first.");
      return;
    }
    let resolvedAgentId = agentId;

    setStep(0);
    setPhase("running");
    try {
      if (agentMode === "new") {
        if (!name.trim()) throw new ApiError(0, "Enter an agent name.");
        const agent = await createAgent({
          name: name.trim(),
          agent_type: agentType,
          config: {
            model: model || null,
            base_url: baseUrl || null,
            api_key: apiKey || null,
            system_prompt: systemPrompt || null,
            // Agentic/multi-agent with no custom endpoint default to the
            // server's configured Claude (Anthropic) account.
            provider: agentType !== "llm_endpoint" && !baseUrl ? "anthropic" : null,
          },
        });
        resolvedAgentId = agent.id;
      }
      if (!resolvedAgentId) throw new ApiError(0, "Select an agent.");

      const ev = await createEvaluation({
        agent_id: resolvedAgentId,
        benchmark_id: benchmarkId,
      });
      const done = await pollEvaluation(ev.id);
      if (done.status === "failed") {
        throw new ApiError(0, done.error || "Evaluation failed on the backend.");
      }
      router.push(`/audit/${ev.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Evaluation failed. Try again.");
      setPhase("form");
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">New Evaluation</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Run an agent over a benchmark in the E2B sandbox and score it with the judge ensemble.
        </p>
      </div>

      <AnimatePresence mode="wait">
        {phase === "form" ? (
          <motion.div key="form" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <Card>
              <CardContent className="space-y-5 pt-6">
                {/* Agent selector */}
                <div>
                  <label className="mb-1.5 block text-sm font-medium">Agent</label>
                  <div className="mb-3 flex items-center rounded-lg border p-0.5">
                    {([["existing", "Use existing"], ["new", "Create new"]] as const).map(([k, l]) => (
                      <button
                        key={k}
                        type="button"
                        onClick={() => setAgentMode(k)}
                        className={cn(
                          "flex-1 rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                          agentMode === k ? "bg-secondary text-foreground" : "text-muted-foreground hover:text-foreground",
                        )}
                      >
                        {l}
                      </button>
                    ))}
                  </div>

                  {agentMode === "existing" ? (
                    agents.length ? (
                      <select
                        value={agentId}
                        onChange={(e) => setAgentId(e.target.value)}
                        className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                      >
                        {agents.map((a) => (
                          <option key={a.id} value={a.id}>
                            {a.name}
                            {a.config?.model ? ` · ${a.config.model}` : ""}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <p className="text-sm text-muted-foreground">
                        No agents yet — switch to “Create new”.
                      </p>
                    )
                  ) : (
                    <div className="space-y-3">
                      <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Agent name *" className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
                      <div>
                        <div className="flex items-center rounded-lg border p-0.5">
                          {AGENT_TYPES.map((t) => (
                            <button
                              key={t.value}
                              type="button"
                              onClick={() => setAgentType(t.value)}
                              className={cn(
                                "flex-1 rounded-md px-2 py-1.5 text-xs font-medium transition-colors",
                                agentType === t.value ? "bg-secondary text-foreground" : "text-muted-foreground hover:text-foreground",
                              )}
                            >
                              {t.label}
                            </button>
                          ))}
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {AGENT_TYPES.find((t) => t.value === agentType)?.hint}
                        </p>
                      </div>
                      <input value={model} onChange={(e) => setModel(e.target.value)} placeholder="Model (optional, e.g. gpt-4o-mini)" className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
                      <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} placeholder="Base URL (optional, OpenAI-compatible)" className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
                      <input value={apiKey} onChange={(e) => setApiKey(e.target.value)} type="password" placeholder="API key (optional — empty = mock agent)" className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
                      <textarea value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)} rows={2} placeholder="System prompt (optional)" className="w-full resize-none rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring" />
                    </div>
                  )}
                </div>

                {/* Benchmark selector */}
                <div>
                  <label className="mb-1.5 block text-sm font-medium">Benchmark</label>
                  {benchmarks.length ? (
                    <select
                      value={benchmarkId}
                      onChange={(e) => setBenchmarkId(e.target.value)}
                      className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
                    >
                      {benchmarks.map((b) => (
                        <option key={b.id} value={b.id}>
                          {b.name} · {b.tasks.length} tasks
                        </option>
                      ))}
                    </select>
                  ) : (
                    <div className="flex items-center justify-between rounded-lg border border-dashed p-3 text-sm">
                      <span className="text-muted-foreground">No benchmarks yet.</span>
                      <Button size="sm" variant="outline" onClick={makeDemoBenchmark} disabled={busy}>
                        {busy ? <Loader2 className="size-4 animate-spin" /> : <Database className="size-4" />} Create sample
                      </Button>
                    </div>
                  )}
                </div>

                {error && <p className="text-sm text-[hsl(var(--danger))]">{error}</p>}

                <Button onClick={run} size="lg" className="w-full" disabled={loading}>
                  <Play /> Run Evaluation
                </Button>

                {benchmarks.length > 0 && (
                  <button onClick={makeDemoBenchmark} disabled={busy} className="flex w-full items-center justify-center gap-1.5 text-xs text-muted-foreground transition-colors hover:text-foreground">
                    <Plus className="size-3" /> add another sample benchmark
                  </button>
                )}
              </CardContent>
            </Card>
            <p className="mt-4 flex items-center justify-center gap-1.5 text-xs text-muted-foreground">
              <ShieldCheck className="size-3.5" /> Runs in the E2B sandbox · graded by the judge ensemble
            </p>
          </motion.div>
        ) : (
          <motion.div key="run" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <Card>
              <CardContent className="pt-6">
                <div className="mb-6 flex items-center gap-3">
                  <span className="grid size-10 place-items-center rounded-lg bg-accent/10 text-accent"><Boxes className="size-5" /></span>
                  <div>
                    <p className="font-semibold">Evaluation in progress</p>
                    <p className="text-xs text-muted-foreground">Agent → sandbox → ensemble judges</p>
                  </div>
                  <Sparkles className="ml-auto size-4 animate-pulse text-accent" />
                </div>
                <div className="space-y-3">
                  {STEPS.map((s, i) => {
                    const state = i < step ? "done" : i === step ? "active" : "todo";
                    return (
                      <div key={s} className="flex items-center gap-3 text-sm">
                        {state === "done" ? <CheckCircle2 className="size-4 text-[hsl(var(--success))]" /> : state === "active" ? <Loader2 className="size-4 animate-spin text-accent" /> : <span className="size-4 rounded-full border" />}
                        <span className={cn(state === "todo" && "text-muted-foreground")}>{s}</span>
                      </div>
                    );
                  })}
                </div>
                <div className="mt-6 h-1.5 overflow-hidden rounded-full bg-secondary">
                  <motion.div className="h-full accent-bg" animate={{ width: `${((step + 1) / STEPS.length) * 100}%` }} transition={{ ease: "easeOut" }} />
                </div>
                <p className="mt-4 text-center text-xs text-muted-foreground">This can take a moment while the sandbox and judges run…</p>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
