"use client";

/**
 * Lightweight analytics.
 *
 * MVP: logs events to the console and a localStorage ring buffer, so you can
 * see the funnel during demos with zero setup. To go live, set
 * NEXT_PUBLIC_POSTHOG_KEY and forward `track()` to PostHog/Plausible — the
 * call sites stay the same.
 */
export function track(event: string, props: Record<string, unknown> = {}) {
  if (typeof window === "undefined") return;
  const payload = { event, props, ts: Date.now() };

  // dev/demo visibility
  // eslint-disable-next-line no-console
  console.debug("[certo:analytics]", event, props);

  try {
    const key = "certo.events";
    const arr = JSON.parse(localStorage.getItem(key) || "[]");
    arr.push(payload);
    localStorage.setItem(key, JSON.stringify(arr.slice(-200)));
  } catch {}

  // production hook (no-op unless configured)
  const w = window as unknown as { posthog?: { capture: (e: string, p: Record<string, unknown>) => void } };
  if (process.env.NEXT_PUBLIC_POSTHOG_KEY && w.posthog) {
    w.posthog.capture(event, props);
  }
}
