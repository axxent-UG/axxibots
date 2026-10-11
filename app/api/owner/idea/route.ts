import { NextRequest, NextResponse } from "next/server";
import { Pool } from "pg";
import { requireSiteAccess } from "@/lib/access";
import { authorize } from "@/lib/auth";
import { isDemo } from "@/lib/config";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const headers = { "Cache-Control": "private, no-store" };
let pool: Pool | undefined;

/** Owner-only action. The existing SQL function enforces proposal state, idempotent
 * eligibility and records the owner's decision in the audit log. No publishing. */
export async function POST(req: NextRequest) {
  const denied = requireSiteAccess(req);
  if (denied) return denied;
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
  if (!process.env.DATABASE_URL)
    return NextResponse.json({ error: "Database is not configured." }, { status: 503, headers });
  try {
    const url = new URL(process.env.DATABASE_URL);
    for (const key of ["sslmode", "sslcert", "sslkey", "sslrootcert"]) url.searchParams.delete(key);
    pool ??= new Pool({ connectionString: url.toString(), max: 2, connectionTimeoutMillis: 8000,
      ssl: { rejectUnauthorized: true, ...(process.env.DATABASE_CA_CERT ? { ca: process.env.DATABASE_CA_CERT } : {}) } });
    const result = await pool.query(
      "SELECT axx.owner_pick_idea($1::uuid, $2::text, $3::text, $4::text) AS result",
      [b.ideaId, b.decision, b.note ?? null, "human:alex:hq"]
    );
    return NextResponse.json({ ok: true, result: result.rows[0]?.result }, { headers });
  } catch (e) {
    // No SQL error details or credentials are returned to the browser.
    const code = (e as { code?: string }).code;
    return NextResponse.json({ error: code === "42501" ? "Database role cannot record owner decisions." :
      "Decision could not be recorded. The idea may no longer be an open proposal, or the database is unavailable." },
      { status: code === "42501" ? 403 : 409, headers });
  }
}
