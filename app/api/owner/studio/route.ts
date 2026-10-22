import { NextRequest, NextResponse } from "next/server";
import { authorizedRpc } from "@/lib/hq-rpc";
import { authorize } from "@/lib/auth";
import { isDemo } from "@/lib/config";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const headers = { "Cache-Control": "private, no-store" };
const actions = {
  release: "axx_hq_release_products",
  archive_legacy: "axx_hq_archive_legacy",
} as const;
/** Owner-only studio actions. Release moves finished products (status qa) to the
 * listing agent, which creates Etsy DRAFTS only. Nothing here publishes a listing. */
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
  const action = body && typeof body === "object" ? (body as Record<string, unknown>).action : undefined;
  if (action !== "release" && action !== "archive_legacy")
    return NextResponse.json({ error: "Unknown action." }, { status: 400, headers });
  try {
    const result = await authorizedRpc(actions[action]);
    return NextResponse.json({ ok: true, result }, { headers });
  } catch {
    return NextResponse.json({ error: "The action could not be completed. Check your session." }, { status: 409, headers });
  }
}
