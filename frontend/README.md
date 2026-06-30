# Certo

**The benchmark, trust & optimization layer for AI agents.**
Connect an AI agent → run an automated security & reliability audit → get an explainable
**Trust Score**, concrete fixes and a shareable certificate.

This is a real, demo-ready MVP. It runs **fully offline** (deterministic audit engine +
localStorage) with **zero external keys** — and is architected so you can plug in OpenAI,
Supabase, Vercel and a custom domain when you're ready.

---

## Run it

```bash
npm install
npm run dev
```

Open http://localhost:3000.

> Behind a TLS-intercepting proxy and `npm install` fails with `UNABLE_TO_VERIFY_LEAF_SIGNATURE`?
> Run: `NODE_OPTIONS=--use-system-ca npm install`
> (PowerShell: `$env:NODE_OPTIONS="--use-system-ca"; npm install`)

## Demo flow (show this with pride)

1. `/` — landing (hero, how-it-works, self-improving, standards, pricing)
2. **Run an audit** → `/new` — pick a sample agent, hit **Run Audit**, watch the 4-step pipeline
3. `/audit/[id]` — the report: Trust Score + Potential Score, score breakdown, standards coverage,
   findings with **evidence + fixes**, **ensemble judges with disagreement detection**, certificate
4. `/dashboard` — history of audited agents

## Architecture

| Layer | MVP (now) | Production (plug in) |
|-------|-----------|----------------------|
| Frontend | Next.js 15 (App Router) + Tailwind + Framer Motion | same |
| Backend | `POST /api/audit` (Next.js route) | same, on Vercel |
| Audit engine | `src/lib/audit-engine.ts` — deterministic, seeded | add OpenAI ensemble judges |
| Storage | `src/lib/store.ts` — localStorage | Supabase |
| Hosting | local | Vercel + custom domain |

Everything the app uses goes through two clean interfaces — `audit-engine.ts` and `store.ts` —
so going live means swapping their internals, not rewriting the app.

## How to connect the real stack later

### 🔑 OpenAI (real LLM-judge ensemble)
1. `OPENAI_API_KEY` in `.env.local`.
2. In `src/app/api/audit/route.ts`, replace the deterministic `runAudit()` ensemble step with real
   calls (GPT-5 / Claude / Gemini) over the fixed rubric, then keep the same aggregation
   (weighted score + confidence + disagreement detection). The response shape stays identical.

### 🗄️ Supabase (persistence)
1. Create a project, add `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
2. Tables: `agents`, `audits` (store the `AuditResult` JSON + columns for filtering).
3. Replace the bodies of `getAudits` / `getAudit` / `saveAudit` in `src/lib/store.ts` with Supabase
   queries (`@supabase/supabase-js`). The component API doesn't change.

### ▲ Vercel + custom domain
1. Push to GitHub → import in Vercel.
2. Add the env vars in Vercel project settings.
3. Add your **custom domain** in Vercel → set `NEXT_PUBLIC_APP_URL` to it (used for share links).

## Tech
Next.js 15 · TypeScript · Tailwind · Framer Motion · Recharts · lucide-react.
