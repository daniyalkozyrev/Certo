"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Footprints, Loader2 } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ApiError, listTraces, type Trace } from "@/lib/api";
import { cn } from "@/lib/utils";

const STATUS_TONE = { completed: "success", running: "warning", failed: "danger" } as const;

export default function TracesPage() {
  const [traces, setTraces] = useState<Trace[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    listTraces()
      .then((p) => setTraces(p.items))
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load traces."));
  }, []);

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
          <Footprints className="size-6" /> Traces
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Trajectories your agents sent to Certo — each scored by the judge across outcome, path and safety.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Ingested runs</CardTitle>
          <CardDescription>
            Instrument your agent with the Certo SDK and call <code className="font-mono">trace.finish()</code> — it appears here, scored.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {error && <p className="text-sm text-[hsl(var(--danger))]">{error}</p>}
          {traces === null && !error && (
            <div className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" /> Loading…
            </div>
          )}
          {traces?.length === 0 && (
            <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground">
              No traces yet. Send one with the SDK or <code className="font-mono">POST /api/v1/traces</code>.
            </div>
          )}
          {traces?.map((t) => {
            const tone = STATUS_TONE[t.status];
            const spans = (t.summary?.n_spans as number | undefined) ?? null;
            return (
              <Link
                key={t.id}
                href={`/traces/${t.id}`}
                className="flex items-center gap-3 rounded-lg border p-4 transition-colors hover:bg-secondary/40"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{t.name || t.task || "Untitled run"}</p>
                  <p className="truncate text-xs text-muted-foreground">
                    {t.source}
                    {spans != null ? ` · ${spans} spans` : ""}
                    {` · ${new Date(t.created_at).toLocaleString()}`}
                  </p>
                </div>
                <Badge variant={tone}>{t.status}</Badge>
                <span
                  className={cn(
                    "w-14 text-right font-mono text-sm font-semibold tabular-nums",
                    (t.trust_score ?? 0) >= 80
                      ? "text-[hsl(var(--success))]"
                      : (t.trust_score ?? 0) >= 50
                        ? "text-[hsl(var(--warning))]"
                        : "text-[hsl(var(--danger))]",
                  )}
                >
                  {t.trust_score != null ? t.trust_score.toFixed(0) : "—"}
                </span>
              </Link>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
}
