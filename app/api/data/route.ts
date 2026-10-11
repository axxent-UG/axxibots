import { NextResponse } from "next/server";
import { isDemo } from "@/lib/config";
import { authorize } from "@/lib/auth";
import { demoSnapshot } from "@/lib/demo";
import { liveSnapshot } from "@/lib/data";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const headers = {
  "Cache-Control": "private, no-store, max-age=0",
  Vary: "Cookie",
};
export async function GET() {
  if (isDemo()) return NextResponse.json(demoSnapshot(), { headers });
  try {
    if (!(await authorize()))
      return NextResponse.json(
        { error: "Sign in with an authorized HQ account." },
        { status: 401, headers },
      );
    return NextResponse.json(await liveSnapshot(), { headers });
  } catch {
    // Never echo database connection strings, raw SQL errors or credentials to clients/logs.
    return NextResponse.json(
      {
        error:
          "Live data unavailable. Check server configuration, database access and schema. No demo data has been substituted.",
      },
      { status: 503, headers },
    );
  }
}
