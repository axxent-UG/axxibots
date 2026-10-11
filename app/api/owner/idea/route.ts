import { NextRequest, NextResponse } from "next/server";
import { authorizedRpc } from "@/lib/hq-rpc";
import { authorize } from "@/lib/auth";
import { isDemo } from "@/lib/config";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const headers = { "Cache-Control": "private, no-store" };


/** Owner-only action. The existing SQL function enforces proposal state, idempotent
 * eligibility and records the owner's decision in the audit log. No publishing. */
export async function POST(req: NextRequest) {
  if (isDemo()) return NextResponse.json({ error: "Actions are disabled in demo mode." }, { status: 403, headers });
  if (req.headers.get("origin") !== req.nextUrl.origin)
    return NextResponse.json({ error: "Invalid origin." }, { status: 403, headers });
  if (!(await authorize()))
    return NextResponse.json({ error: "Sign in with your authorized HQ account." }, { status: 401, headers });
  let body: unknown;
  try { body = await req.json(); } catch {
    return NextResponse.json({ error: "Invalid request." }, { status: 400, headers });
  }
  if (!body || typeof body !== "object")
    return NextResponse.json({ error: "Invalid request." }, { status: 400, headers });
  const b = body as Record<string, unknown>;
  if (typeof b.ideaId !== "string" || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(b.ideaId)
    || !["APPROVED", "REJECTED"].includes(String(b.decision))
    || (b.note !== undefined && (typeof b.note !== "string" || b.note.length > 2000)))
    return NextResponse.json({ error: "Invalid decision." }, { status: 400, headers });
  try {
    const result = await authorizedRpc("axx_hq_owner_decision", {
      p_idea: b.ideaId,
      p_decision: b.decision,
      p_note: b.note ?? null,
    });
    return NextResponse.json({ ok: true, result }, { headers });
  } catch {
    return NextResponse.json({ error: "Owner decision could not be recorded. Check proposal eligibility or session." }, { status: 409, headers });
  }
}
