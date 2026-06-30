"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Check, Download, Link2, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { TrustRing } from "@/components/trust-ring";
import { Logo } from "@/components/logo";
import { ApiError, getEvaluation, type EvaluationDetail } from "@/lib/api";
import { CERT_META, certificationFor } from "@/lib/trust";
import { track } from "@/lib/analytics";
import { formatRelativeTime } from "@/lib/utils";

export default function CertificatePage() {
  const params = useParams<{ id: string }>();
  const [ev, setEv] = useState<EvaluationDetail | null | undefined>(undefined);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    getEvaluation(params.id)
      .then(setEv)
      .catch((e) => setEv(e instanceof ApiError && e.status === 404 ? null : null));
    track("cert_view", { id: params.id });
  }, [params.id]);

  function copyLink() {
    navigator.clipboard?.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
    track("cert_share", { id: params.id });
  }

  if (ev === undefined) return <div className="grid min-h-screen place-items-center text-sm text-muted-foreground">Loading…</div>;
  if (ev === null || ev.status !== "completed")
    return (
      <div className="grid min-h-screen place-items-center px-4 text-center">
        <div>
          <p className="font-medium">Certificate unavailable</p>
          <p className="mt-1 text-sm text-muted-foreground">This evaluation does not exist or has not completed.</p>
          <Link href="/" className="mt-4 inline-block"><Button>Go to Certo</Button></Link>
        </div>
      </div>
    );

  const trust = ev.trust_score ?? 0;
  const cert = certificationFor(trust);
  const meta = CERT_META[cert];
  const nTasks = ev.results.length;
  const nPassed = ev.results.filter((r) => (r.reward ?? -1) > 0).length;

  return (
    <div className="min-h-screen bg-secondary/30 py-10">
      <div className="mx-auto max-w-2xl px-4">
        <div className="mb-5 flex items-center justify-between print:hidden">
          <Link href="/"><Logo /></Link>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={copyLink}>{copied ? <><Check className="size-4 text-[hsl(var(--success))]" /> Copied</> : <><Link2 /> Copy link</>}</Button>
            <Button size="sm" onClick={() => window.print()}><Download /> Download PDF</Button>
          </div>
        </div>

        <div className="overflow-hidden rounded-2xl border bg-card shadow-xl">
          <div className="relative px-8 py-8" style={{ background: `linear-gradient(135deg, ${meta.color}1f, transparent 70%)` }}>
            <div className="pointer-events-none absolute inset-0 grid-bg opacity-[0.1]" />
            <div className="relative flex items-start justify-between">
              <div>
                <p className="text-[11px] uppercase tracking-[0.25em] text-muted-foreground">Certo Certificate of Trust</p>
                <h1 className="mt-2 text-2xl font-semibold tracking-tight">Evaluation {ev.id.slice(0, 8)}</h1>
                <p className="font-mono text-xs text-muted-foreground">{ev.id}</p>
              </div>
              <span className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium ring-1" style={{ color: meta.color, background: `${meta.color}14`, borderColor: `${meta.color}40` }}>
                <ShieldCheck className="size-4" /> {cert}
              </span>
            </div>

            <div className="relative mt-7 flex flex-wrap items-center gap-7">
              <TrustRing score={trust} size={150} />
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">Certified level</p>
                <p className="text-3xl font-semibold" style={{ color: meta.color }}>{cert}</p>
                <p className="max-w-xs text-xs text-muted-foreground">{meta.blurb}</p>
              </div>
            </div>

            <div className="relative mt-7 grid grid-cols-2 gap-3 border-t pt-6 text-center sm:grid-cols-3">
              <Stat label="TrustScore" value={trust.toFixed(0)} />
              <Stat label="Pass rate" value={`${Math.round((ev.pass_rate ?? 0) * 100)}%`} />
              <Stat label="Tasks passed" value={`${nPassed}/${nTasks}`} />
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 border-t px-8 py-5 text-xs text-muted-foreground">
            <span>Certificate No. <span className="font-mono text-foreground">CERTO-2026-{ev.id.slice(0, 8).toUpperCase()}</span></span>
            <span>Issued {formatRelativeTime(ev.created_at)} · Verified by Certo</span>
          </div>
        </div>

        <p className="mt-5 text-center text-xs text-muted-foreground print:hidden">
          Want a certificate for your agent? <Link href="/new" className="font-medium text-accent hover:underline">Run an evaluation →</Link>
        </p>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-0.5 font-semibold tabular-nums">{value}</p>
    </div>
  );
}
