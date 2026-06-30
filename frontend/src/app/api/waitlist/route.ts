import { NextResponse } from "next/server";

/**
 * POST /api/waitlist — capture an email lead.
 *
 * MVP: validates + logs (in-memory). To go live, write to Supabase
 * (table: waitlist) or forward to a CRM / email tool — one function swap.
 */
const seen = new Set<string>();

export async function POST(req: Request) {
  let body: { email?: string; source?: string };
  try { body = await req.json(); } catch { return NextResponse.json({ error: "Invalid JSON" }, { status: 400 }); }

  const email = (body.email || "").trim().toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return NextResponse.json({ error: "Invalid email" }, { status: 400 });
  }

  seen.add(email);
  // eslint-disable-next-line no-console
  console.log(`[certo:waitlist] ${email} (source=${body.source ?? "unknown"}) total=${seen.size}`);

  // TODO(production): persist to Supabase
  //   await supabase.from("waitlist").insert({ email, source: body.source });

  return NextResponse.json({ ok: true });
}
