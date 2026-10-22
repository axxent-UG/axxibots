import { NextResponse } from "next/server";
import { isDemo } from "@/lib/config";
import { authorize } from "@/lib/auth";
import { authorizedRpc } from "@/lib/hq-rpc";
import { demoStudio } from "@/lib/studio";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const headers = { "Cache-Control": "private, no-store, max-age=0", Vary: "Cookie" };
export async function GET() {
  if (isDemo()) return NextResponse.json(demoStudio, { headers });
  try {
    if (!(await authorize()))
      return NextResponse.json({ error: "Sign in with an authorized HQ account." }, { status: 401, headers });
    return NextResponse.json(await authorizedRpc("axx_hq_studio"), { headers });
  } catch {
    return NextResponse.json({ error: "Studio data unavailable." }, { status: 503, headers });
  }
}
