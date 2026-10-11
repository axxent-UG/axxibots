import { NextResponse, type NextRequest } from "next/server";
import { authClient, clearSession } from "@/lib/auth";
import { isDemo } from "@/lib/config";
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
    if (isDemo()) return NextResponse.json({ error: "Login unavailable in demo mode." }, { status: 400 });
    if (body.action !== "magic_link" || typeof body.email !== "string" || body.email.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(body.email))
      return NextResponse.json({ error: "Enter a valid email address." }, { status: 400 });
    // shouldCreateUser:false prevents registration and preserves the existing allowlist.
    const { error } = await authClient().auth.signInWithOtp({
      email: body.email,
      options: { shouldCreateUser: false, emailRedirectTo: req.nextUrl.origin + "/auth/callback" },
    });
    if (error) return NextResponse.json({ error: "Unable to send sign-in link. Check the authorized account and Supabase email configuration." }, { status: 400 });
    return NextResponse.json({ ok: true, message: "If the account is registered, check your inbox for a sign-in link." }, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ error: "Authentication service unavailable." }, { status: 503 });
  }
}
