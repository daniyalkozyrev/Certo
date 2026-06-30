"use client";

import { useState } from "react";
import { ArrowRight, CheckCircle2, Loader2 } from "lucide-react";
import { track } from "@/lib/analytics";

export function Waitlist({ source = "landing" }: { source?: string }) {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [msg, setMsg] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { setState("error"); setMsg("Enter a valid email."); return; }
    setState("loading");
    try {
      const res = await fetch("/api/waitlist", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, source }) });
      if (!res.ok) throw new Error();
      track("waitlist_signup", { source });
      setState("done");
    } catch {
      setState("error"); setMsg("Something went wrong. Try again.");
    }
  }

  if (state === "done") {
    return (
      <div className="flex items-center justify-center gap-2 rounded-xl border border-[hsl(var(--success)/0.3)] bg-[hsl(var(--success)/0.08)] px-4 py-3 text-sm font-medium text-[hsl(var(--success))]">
        <CheckCircle2 className="size-4" /> You&apos;re on the list — we&apos;ll be in touch.
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="mx-auto flex max-w-md flex-col gap-2 sm:flex-row">
      <input
        type="email" value={email} onChange={(e) => { setEmail(e.target.value); setState("idle"); }}
        placeholder="you@company.com"
        className="h-11 flex-1 rounded-lg border bg-background px-4 text-sm outline-none focus:ring-2 focus:ring-ring"
      />
      <button type="submit" disabled={state === "loading"} className="inline-flex h-11 items-center justify-center gap-2 rounded-lg accent-bg px-5 text-sm font-medium text-white shadow-sm transition-all hover:brightness-110 disabled:opacity-60">
        {state === "loading" ? <Loader2 className="size-4 animate-spin" /> : <>Get early access <ArrowRight className="size-4" /></>}
      </button>
      {state === "error" && <p className="text-xs text-[hsl(var(--danger))] sm:absolute sm:mt-12">{msg}</p>}
    </form>
  );
}
