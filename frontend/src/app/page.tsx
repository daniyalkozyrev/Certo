"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowRight, Boxes, CheckCircle2, ChevronDown, Eye, FileCheck2, Gauge,
  Minus, ScanSearch, ShieldAlert, ShieldCheck, Sparkles, Wrench,
} from "lucide-react";
import { Logo } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { TrustRing } from "@/components/trust-ring";
import { AnimatedNumber } from "@/components/animated-number";
import { Waitlist } from "@/components/waitlist";
import { FrameworkChip, FRAMEWORKS_BRAND, BrandTile, PROVIDERS } from "@/components/brand-marks";

const fadeUp = {
  initial: { opacity: 0, y: 26 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, margin: "-80px" },
  transition: { duration: 0.7, ease: [0.16, 1, 0.3, 1] as const },
};

export default function Landing() {
  return (
    <div className="relative overflow-x-clip">
      <header className="sticky top-0 z-50 border-b border-border/60 glass">
        <div className="container flex h-16 items-center justify-between">
          <Logo />
          <nav className="hidden items-center gap-8 text-sm text-muted-foreground md:flex">
            <a href="#how" className="transition-colors hover:text-foreground">How it works</a>
            <a href="#fix" className="transition-colors hover:text-foreground">Self-improving</a>
            <a href="#standards" className="transition-colors hover:text-foreground">Standards</a>
            <a href="#pricing" className="transition-colors hover:text-foreground">Pricing</a>
          </nav>
          <div className="flex items-center gap-2">
            <Link href="/login"><Button variant="ghost" size="sm">Sign in</Button></Link>
            <Link href="/dashboard"><Button size="sm" className="shine">Open dashboard <ArrowRight /></Button></Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative">
        <div className="aurora opacity-70" />
        <div className="pointer-events-none absolute inset-0 grid-bg radial-fade opacity-50" />
        <div className="container relative pb-16 pt-20 md:pt-28">
          <motion.div {...fadeUp} className="mx-auto max-w-3xl text-center">
            <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.5 }}>
              <Badge variant="accent" className="mb-6"><Sparkles className="size-3" /> The benchmark, trust & optimization layer for AI agents</Badge>
            </motion.div>
            <h1 className="text-balance text-5xl font-semibold tracking-tight md:text-7xl">
              Ship AI agents <span className="accent-grad">you can trust.</span>
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-balance text-lg text-muted-foreground md:text-xl">
              Connect an agent, run an automated security &amp; reliability audit, and get an explainable
              Trust Score, concrete fixes and a shareable certificate — in minutes.
            </p>
            <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <Link href="/new"><Button size="lg" className="w-full shine sm:w-auto">Audit your agent <ArrowRight /></Button></Link>
              <Link href="/dashboard"><Button size="lg" variant="outline" className="w-full sm:w-auto">View live demo</Button></Link>
            </div>
            <p className="mt-4 text-xs text-muted-foreground">No credit card · OWASP / NIST / EU AI Act aligned · Set up in minutes</p>
          </motion.div>

          {/* Hero preview */}
          <motion.div initial={{ opacity: 0, y: 48 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, delay: 0.2, ease: [0.16, 1, 0.3, 1] }} className="mx-auto mt-16 max-w-4xl">
            <div className="rounded-2xl border bg-card/80 p-2 shadow-2xl shadow-primary/10 backdrop-blur">
              <div className="grid gap-px overflow-hidden rounded-xl border bg-border sm:grid-cols-[1fr_260px]">
                <div className="bg-background p-6">
                  <div className="flex items-center justify-between">
                    <div><p className="text-xs text-muted-foreground">Audit report</p><p className="text-lg font-semibold">Atlas SDR Agent</p></div>
                    <Badge variant="success"><ShieldCheck className="size-3" /> Gold</Badge>
                  </div>
                  <div className="mt-5 space-y-3">
                    {[{ l: "Security", v: 88 }, { l: "Reliability", v: 91 }, { l: "Accuracy", v: 86 }].map((m, i) => (
                      <div key={m.l} className="space-y-1.5">
                        <div className="flex justify-between text-sm"><span className="font-medium">{m.l}</span><span className="font-mono text-muted-foreground">{m.v}</span></div>
                        <div className="h-2 overflow-hidden rounded-full bg-secondary"><motion.div className="h-full rounded-full accent-bg" initial={{ width: 0 }} animate={{ width: `${m.v}%` }} transition={{ duration: 1, delay: 0.6 + i * 0.15 }} /></div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-5 rounded-lg border bg-secondary/40 p-3 text-xs"><span className="font-medium text-[hsl(var(--danger))]">2 findings</span> <span className="text-muted-foreground">· Prompt Injection (−8) · PII Leakage (−7) → fixes available</span></div>
                </div>
                <div className="flex flex-col items-center justify-center bg-card p-6"><TrustRing score={84} potential={94} size={150} /></div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Frameworks marquee */}
      <section className="border-y bg-secondary/30 py-7">
        <p className="mb-5 text-center text-xs font-medium uppercase tracking-widest text-muted-foreground">Works with every agent framework</p>
        <div className="marquee-mask">
          <div className="marquee">
            {[...FRAMEWORKS_BRAND, ...FRAMEWORKS_BRAND].map((f, i) => <FrameworkChip key={i} fw={f} />)}
          </div>
        </div>
      </section>

      {/* LLM judges */}
      <section className="container py-14">
        <p className="mb-7 text-center text-xs font-medium uppercase tracking-widest text-muted-foreground">Powered by an ensemble of frontier models</p>
        <div className="flex flex-wrap items-center justify-center gap-x-9 gap-y-5">
          {PROVIDERS.map((p, i) => (
            <motion.div key={p.name} {...fadeUp} transition={{ ...fadeUp.transition, delay: i * 0.06 }}>
              <BrandTile provider={p} label size={42} />
            </motion.div>
          ))}
        </div>
      </section>

      {/* Social proof */}
      <section className="container py-16">
        <div className="grid grid-cols-1 gap-8 sm:grid-cols-4">
          {[
            { v: 20, suffix: "+", l: "attack vectors tested" },
            { v: 3, suffix: "", l: "frontier judge models" },
            { v: 6, suffix: "", l: "agent frameworks supported" },
            { v: 4, suffix: "", l: "standards aligned" },
          ].map((s, i) => (
            <motion.div key={s.l} {...fadeUp} transition={{ ...fadeUp.transition, delay: i * 0.1 }} className="text-center">
              <div className="text-4xl font-semibold tracking-tight md:text-5xl"><AnimatedNumber value={s.v} suffix={s.suffix} decimals={0} /></div>
              <div className="mt-1 text-sm text-muted-foreground">{s.l}</div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Problem */}
      <section className="border-y bg-secondary/30">
        <div className="container py-24">
          <motion.div {...fadeUp} className="mx-auto max-w-2xl text-center">
            <Badge variant="outline" className="mb-4">The problem</Badge>
            <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">Teams deploy AI agents they can&apos;t measure.</h2>
            <p className="mt-4 text-muted-foreground">Before an agent touches real data or closes a deal, security and compliance demand proof it&apos;s safe. Today that proof is manual, slow, and inconsistent.</p>
          </motion.div>
          <div className="mt-14 grid gap-6 md:grid-cols-3">
            {[
              { icon: Eye, t: "No visibility", d: "Agents run in production with zero objective insight into accuracy, drift or failure modes." },
              { icon: ShieldAlert, t: "No safety floor", d: "Hallucinations, jailbreaks and data leaks surface only after they cost you a customer." },
              { icon: FileCheck2, t: "No standard", d: "There's no credit score for agents — no way to prove trust to a buyer or a regulator." },
            ].map((p, i) => (
              <motion.div key={p.t} {...fadeUp} transition={{ ...fadeUp.transition, delay: i * 0.1 }} className="rounded-xl border bg-card p-7 lift">
                <div className="mb-5 grid size-11 place-items-center rounded-lg bg-secondary text-foreground"><p.icon className="size-5" /></div>
                <h3 className="text-lg font-semibold">{p.t}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{p.d}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="container py-24">
        <motion.div {...fadeUp} className="mx-auto max-w-2xl text-center">
          <Badge variant="outline" className="mb-4">How it works</Badge>
          <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">From agent to certificate in 4 steps.</h2>
          <p className="mt-4 text-muted-foreground">A real evaluation pipeline — deterministic checks, ground truth, and an LLM judge ensemble with disagreement detection.</p>
        </motion.div>
        <div className="mt-14 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          {[
            { icon: Boxes, t: "Connect", d: "API, logs or test env — OpenAI SDK, LangGraph, CrewAI, PydanticAI." },
            { icon: ScanSearch, t: "Scan", d: "Red-team attacks, reliability and accuracy tests run automatically." },
            { icon: Gauge, t: "Score", d: "Explainable Trust Score with per-finding impact and a Potential Score." },
            { icon: FileCheck2, t: "Certify", d: "Shareable certificate, Bronze → Diamond, mapped to standards." },
          ].map((f, i) => (
            <motion.div key={f.t} {...fadeUp} transition={{ ...fadeUp.transition, delay: i * 0.08 }} className="group rounded-xl border bg-card p-6 lift shine">
              <div className="mb-5 grid size-11 place-items-center rounded-lg bg-accent/10 text-accent transition-transform group-hover:scale-110"><f.icon className="size-5" /></div>
              <div className="mb-1 font-mono text-xs text-muted-foreground">0{i + 1}</div>
              <h3 className="font-semibold">{f.t}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{f.d}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Self-improving */}
      <section id="fix" className="border-y bg-secondary/30">
        <div className="container grid items-center gap-12 py-24 lg:grid-cols-2">
          <motion.div {...fadeUp}>
            <Badge variant="accent" className="mb-4"><Wrench className="size-3" /> Self-improving</Badge>
            <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">Don&apos;t just score it. Fix it.</h2>
            <p className="mt-4 text-muted-foreground">Certo shows your Trust Score and your Potential Score — and the exact fixes to close the gap. Apply them and watch the score climb.</p>
            <ul className="mt-8 space-y-3">
              {["Find → Explain → Impact → Recommend → Re-audit", "Each finding shows evidence and expected score gain", "v2: generate the fix (prompt, guardrails, config, patch)", "v3: apply the fix via GitHub PR"].map((t) => (
                <li key={t} className="flex items-start gap-3 text-sm"><CheckCircle2 className="mt-0.5 size-4 shrink-0 text-[hsl(var(--success))]" /><span className="text-muted-foreground">{t}</span></li>
              ))}
            </ul>
          </motion.div>
          <motion.div {...fadeUp} transition={{ ...fadeUp.transition, delay: 0.15 }} className="rounded-2xl border bg-card p-6 shadow-xl shadow-primary/5">
            <div className="flex items-center justify-between"><span className="font-mono text-sm">Trust Score</span><span className="font-mono text-2xl font-semibold">76 <span className="text-muted-foreground">→</span> <span className="accent-grad">92</span></span></div>
            <div className="mt-4 space-y-2 text-sm">
              {["Update system prompt", "Add input guardrail", "Restrict tool access", "Add output validation"].map((f, i) => (
                <motion.div key={f} {...fadeUp} transition={{ ...fadeUp.transition, delay: 0.2 + i * 0.08 }} className="flex items-center justify-between rounded-lg border bg-secondary/40 px-3 py-2">
                  <span className="flex items-center gap-2"><span className="grid size-5 place-items-center rounded-full bg-accent/10 text-[11px] font-medium text-accent">{i + 1}</span>{f}</span>
                  <span className="font-mono text-xs text-[hsl(var(--success))]">+{[6, 4, 5, 3][i]}</span>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* Standards */}
      <section id="standards" className="container py-24 text-center">
        <motion.div {...fadeUp} className="mx-auto max-w-2xl">
          <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">Aligned with the standards buyers ask for.</h2>
          <p className="mt-4 text-muted-foreground">Certo maps every check to recognized frameworks — so passing Certo helps you pass procurement and the regulator.</p>
        </motion.div>
        <div className="mx-auto mt-10 flex max-w-3xl flex-wrap items-center justify-center gap-3">
          {["OWASP LLM Top 10", "NIST AI RMF", "EU AI Act", "ISO/IEC 42001"].map((s, i) => (
            <motion.span key={s} {...fadeUp} transition={{ ...fadeUp.transition, delay: i * 0.06 }} className="rounded-full border bg-card px-5 py-2.5 text-sm font-medium shadow-sm lift">{s}</motion.span>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="border-y bg-secondary/30">
        <div className="container py-24">
          <motion.div {...fadeUp} className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">Pricing that grows with you.</h2>
            <p className="mt-4 text-muted-foreground">Start free. Upgrade when trust becomes mission-critical.</p>
          </motion.div>
          <div className="mx-auto mt-14 grid max-w-5xl gap-6 lg:grid-cols-3">
            {[
              { name: "Starter", price: "$99", blurb: "For small teams & agencies.", features: ["Up to 3 agents", "Trust + Potential Score", "Fix recommendations", "Email support"], featured: false },
              { name: "Growth", price: "$349", blurb: "For teams shipping to prod.", features: ["Up to 15 agents", "Continuous monitoring", "Generate Fix", "Standards mapping", "Priority support"], featured: true },
              { name: "Enterprise", price: "Custom", blurb: "For banks & regulated orgs.", features: ["Unlimited agents", "Apply Fix (auto-PR)", "SSO + audit logs", "On-prem / VPC", "Dedicated CSM"], featured: false },
            ].map((tier, i) => (
              <motion.div key={tier.name} {...fadeUp} transition={{ ...fadeUp.transition, delay: i * 0.08 }} className={`relative rounded-2xl border bg-card p-7 lift ${tier.featured ? "border-accent shadow-xl shadow-accent/10 ring-1 ring-accent" : ""}`}>
                {tier.featured && <Badge variant="accent" className="absolute -top-3 left-7">Most popular</Badge>}
                <h3 className="font-semibold">{tier.name}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{tier.blurb}</p>
                <div className="mt-5 flex items-baseline gap-1"><span className="text-4xl font-semibold tracking-tight">{tier.price}</span>{tier.price !== "Custom" && <span className="text-sm text-muted-foreground">/mo</span>}</div>
                <Link href="/new" className="mt-6 block"><Button variant={tier.featured ? "default" : "outline"} className="w-full">Get started</Button></Link>
                <ul className="mt-7 space-y-3">{tier.features.map((f) => (<li key={f} className="flex items-center gap-2.5 text-sm"><CheckCircle2 className="size-4 shrink-0 text-[hsl(var(--success))]" /><span className="text-muted-foreground">{f}</span></li>))}</ul>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="container py-24">
        <motion.div {...fadeUp} className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-semibold tracking-tight md:text-4xl">Questions, answered.</h2>
        </motion.div>
        <div className="mx-auto mt-10 max-w-2xl divide-y rounded-2xl border bg-card">
          {[
            { q: "Do you train your own model to score agents?", a: "No. Certo combines deterministic rule-based checks, ground-truth eval, and an ensemble of frontier LLM judges (GPT-5 / Claude / Gemini) with disagreement detection — so the score is objective and explainable." },
            { q: "How do you connect to my agent?", a: "Via API endpoint, uploaded logs, or a test environment. We support OpenAI Agents SDK, LangGraph, CrewAI, PydanticAI and custom APIs." },
            { q: "Is my data safe?", a: "Yes. We minimize stored data, isolate each customer, encrypt in transit and at rest, and offer on-prem / VPC deployment for regulated teams." },
            { q: "What standards do you map to?", a: "OWASP LLM Top 10, NIST AI RMF, EU AI Act and ISO/IEC 42001 — so passing Certo helps you pass procurement and the regulator." },
          ].map((item) => <Faq key={item.q} {...item} />)}
        </div>
      </section>

      {/* Waitlist */}
      <section id="waitlist" className="container py-20">
        <motion.div {...fadeUp} className="mx-auto max-w-xl rounded-2xl border bg-card p-8 text-center shadow-sm">
          <Badge variant="accent" className="mb-4"><Sparkles className="size-3" /> Early access</Badge>
          <h2 className="text-2xl font-semibold tracking-tight">Be first to certify your agents.</h2>
          <p className="mt-2 text-sm text-muted-foreground">Join the waitlist — we&apos;re onboarding design partners now.</p>
          <div className="mt-6"><Waitlist source="landing" /></div>
        </motion.div>
      </section>

      {/* CTA */}
      <section className="container py-24">
        <motion.div {...fadeUp} className="relative overflow-hidden rounded-3xl bg-primary px-8 py-16 text-center text-primary-foreground">
          <div className="pointer-events-none absolute inset-0 grid-bg opacity-10" />
          <h2 className="relative text-3xl font-semibold tracking-tight md:text-4xl">Today they ask &ldquo;Do you have SOC2?&rdquo;</h2>
          <p className="relative mx-auto mt-4 max-w-xl text-primary-foreground/70">Tomorrow they&apos;ll ask &ldquo;Did your AI agent pass Certo?&rdquo; Give your agents a score they have to earn.</p>
          <Link href="/new" className="relative mt-8 inline-block"><Button size="lg" variant="default" className="shine">Run your first audit <ArrowRight /></Button></Link>
        </motion.div>
      </section>

      <footer className="border-t">
        <div className="container flex flex-col items-center justify-between gap-4 py-10 text-sm text-muted-foreground md:flex-row">
          <Logo />
          <p>© 2026 Certo. The trust layer for AI agents.</p>
          <div className="flex gap-6"><a href="#" className="hover:text-foreground">Privacy</a><a href="#" className="hover:text-foreground">Docs</a></div>
        </div>
      </footer>
    </div>
  );
}

function Faq({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="p-5">
      <button onClick={() => setOpen((o) => !o)} className="flex w-full items-center justify-between gap-4 text-left">
        <span className="font-medium">{q}</span>
        {open ? <Minus className="size-4 shrink-0 text-muted-foreground" /> : <ChevronDown className="size-4 shrink-0 text-muted-foreground" />}
      </button>
      <motion.div initial={false} animate={{ height: open ? "auto" : 0, opacity: open ? 1 : 0 }} transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }} className="overflow-hidden">
        <p className="pt-3 text-sm text-muted-foreground">{a}</p>
      </motion.div>
    </div>
  );
}
