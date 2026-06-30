"use client";

import { useEffect, useState } from "react";
import {
  Bell, Check, Cpu, Monitor, Moon, Palette, Plug, RefreshCw, Scale, Server, Sun, X,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { API_BASE, health } from "@/lib/api";
import { useTheme, type Theme } from "@/components/theme-provider";
import { cn } from "@/lib/utils";

const THEMES: { value: Theme; label: string; icon: typeof Sun }[] = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
];

// TrustScore weighting (mirrors the backend scoring module — informational).
const SCORING = [
  { label: "Judge consensus (normalized 1–5)", weight: 1.0 },
];

const JUDGES = [
  { name: "Prometheus-2", role: "Primary judge · self-hosted vLLM", on: true },
  { name: "Secondary LLM", role: "Plug-in slot — set JUDGE_SECONDARY_* on the backend", on: false },
];

export default function SettingsPage() {
  const [status, setStatus] = useState<"idle" | "checking" | "ok" | "fail">("idle");
  const [env, setEnv] = useState<string>("");
  const { theme, setTheme } = useTheme();
  const [emailAlerts, setEmailAlerts] = useState(false);

  useEffect(() => {
    setEmailAlerts(localStorage.getItem("certo.emailAlerts") === "true");
  }, []);

  function toggleEmailAlerts() {
    const next = !emailAlerts;
    setEmailAlerts(next);
    localStorage.setItem("certo.emailAlerts", String(next));
  }

  async function check() {
    setStatus("checking");
    try {
      const h = await health();
      setEnv(h.env);
      setStatus("ok");
    } catch {
      setStatus("fail");
    }
  }

  useEffect(() => {
    check();
  }, []);

  return (
    <div className="space-y-6">
      <div><h1 className="text-2xl font-semibold tracking-tight">Settings</h1><p className="mt-1 text-sm text-muted-foreground">Backend connection, the judge ensemble and the scoring model.</p></div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Appearance */}
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Palette className="size-4" /> Appearance</CardTitle><CardDescription>Theme used across the dashboard</CardDescription></CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium">Theme</label>
              <div className="grid grid-cols-3 gap-2">
                {THEMES.map((t) => (
                  <button
                    key={t.value}
                    onClick={() => setTheme(t.value)}
                    className={cn(
                      "flex flex-col items-center gap-1.5 rounded-lg border p-3 text-xs font-medium transition-colors",
                      theme === t.value
                        ? "border-accent bg-accent/10 text-accent"
                        : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground",
                    )}
                  >
                    <t.icon className="size-4" />
                    {t.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div className="flex items-center gap-2 text-sm">
                <Bell className="size-4 text-muted-foreground" />
                <div>
                  <p className="font-medium">Email alerts</p>
                  <p className="text-xs text-muted-foreground">Notify me when an evaluation finishes</p>
                </div>
              </div>
              <button
                onClick={toggleEmailAlerts}
                role="switch"
                aria-checked={emailAlerts}
                className={cn(
                  "relative h-6 w-11 shrink-0 rounded-full transition-colors",
                  emailAlerts ? "accent-bg" : "bg-secondary",
                )}
              >
                <span className={cn(
                  "absolute top-0.5 size-5 rounded-full bg-white shadow transition-transform",
                  emailAlerts ? "translate-x-[22px]" : "translate-x-0.5",
                )} />
              </button>
            </div>
          </CardContent>
        </Card>

        {/* Backend connection */}
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Server className="size-4" /> Backend connection</CardTitle><CardDescription>FastAPI API the dashboard talks to</CardDescription></CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium">API base URL</label>
              <code className="block truncate rounded-lg border bg-secondary/40 px-3 py-2 font-mono text-sm">{API_BASE}</code>
              <p className="mt-1.5 text-xs text-muted-foreground">Set <code className="font-mono">NEXT_PUBLIC_API_URL</code> in <code className="font-mono">.env.local</code> to change it.</p>
            </div>
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div className="flex items-center gap-2 text-sm">
                {status === "ok" && <Badge variant="success"><Check className="size-3" /> Connected{env ? ` · ${env}` : ""}</Badge>}
                {status === "fail" && <Badge variant="danger"><X className="size-3" /> Unreachable</Badge>}
                {(status === "idle" || status === "checking") && <Badge variant="accent">Checking…</Badge>}
              </div>
              <Button size="sm" variant="outline" onClick={check} disabled={status === "checking"}><RefreshCw className={status === "checking" ? "size-4 animate-spin" : "size-4"} /> Test</Button>
            </div>
          </CardContent>
        </Card>

        {/* Judge ensemble */}
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Cpu className="size-4" /> Judge ensemble</CardTitle><CardDescription>Multiple judges reduce single-model subjectivity</CardDescription></CardHeader>
          <CardContent className="space-y-3">
            {JUDGES.map((j) => (
              <div key={j.name} className="flex items-center justify-between rounded-lg border p-3">
                <div className="min-w-0">
                  <p className="text-sm font-medium">{j.name}</p>
                  <p className="truncate text-xs text-muted-foreground">{j.role}</p>
                </div>
                {j.on ? <Badge variant="success"><Check className="size-3" /> On</Badge> : <Badge variant="warning">Optional</Badge>}
              </div>
            ))}
            <p className="text-xs text-muted-foreground">Enable the second judge on the backend to average an independent opinion into the consensus.</p>
          </CardContent>
        </Card>

        {/* Scoring model */}
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Scale className="size-4" /> TrustScore model</CardTitle><CardDescription>How the 0–100 score is computed</CardDescription></CardHeader>
          <CardContent className="space-y-4">
            {SCORING.map((s) => (
              <div key={s.label} className="space-y-1.5">
                <div className="flex items-center justify-between text-sm"><span className="font-medium">{s.label}</span><span className="font-mono text-muted-foreground">{Math.round(s.weight * 100)}%</span></div>
                <div className="h-2 overflow-hidden rounded-full bg-secondary"><div className="h-full rounded-full accent-bg" style={{ width: `${s.weight * 100}%` }} /></div>
              </div>
            ))}
            <p className="text-xs text-muted-foreground">TrustScore = 100 × weighted mean of normalized judge consensus. Pass rate is reported separately. Extra dimensions (safety, efficiency) plug into the same scoring module.</p>
          </CardContent>
        </Card>

        {/* Integrations */}
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Plug className="size-4" /> Pipeline</CardTitle><CardDescription>External services in the run</CardDescription></CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
            {[
              { name: "E2B", desc: "Sandbox execution" },
              { name: "vLLM", desc: "Prometheus-2 host" },
              { name: "Postgres", desc: "Persistence" },
              { name: "Redis", desc: "Job queue (Arq)" },
            ].map((it) => (
              <div key={it.name} className="flex items-center justify-between rounded-lg border p-3">
                <div className="flex items-center gap-3">
                  <span className="grid size-9 place-items-center rounded-lg bg-secondary text-sm font-semibold">{it.name.slice(0, 2)}</span>
                  <div><p className="text-sm font-medium">{it.name}</p><p className="text-xs text-muted-foreground">{it.desc}</p></div>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
