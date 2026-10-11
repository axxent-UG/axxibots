import { NextResponse, type NextRequest } from "next/server";
import { authClient, saveSession, clearSession } from "@/lib/auth";
import { allowedUser, isDemo } from "@/lib/config";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function POST(req: NextRequest) {
  if (req.headers.get("origin") !== req.nextUrl.origin)
    return NextResponse.json({ error: "Invalid origin" }, { status: 403 });
  try {
    const body = await req.json();
    if (body.action === "logout") {
      await clearSession();
      return NextResponse.json({ ok: true });
    }
    if (isDemo())
      return NextResponse.json(
        { error: "Demo mode uses sample data; login is disabled." },
        { status: 400 },
      );
    if (
      typeof body.email !== "string" ||
      typeof body.password !== "string" ||
      body.email.length > 254 ||
      body.password.length > 1024
    )
      return NextResponse.json(
        { error: "Invalid sign-in details" },
        { status: 400 },
      );
    const { data, error } = await authClient().auth.signInWithPassword({
      email: body.email,
      password: body.password,
    });
    if (error || !data.user || !data.session || !allowedUser(data.user.id))
      return NextResponse.json(
        { error: "Sign-in failed or this account is not authorized for HQ." },
        { status: 401 },
      );
    await saveSession(
      data.session.access_token,
      data.session.refresh_token,
      data.session.expires_in,
    );
    return NextResponse.json(
      { ok: true },
      { headers: { "Cache-Control": "no-store" } },
    );
  } catch {
    return NextResponse.json(
      { error: "Authentication unavailable. Check server configuration." },
      { status: 503 },
    );
  }
}
