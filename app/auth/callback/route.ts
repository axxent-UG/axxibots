import { NextRequest, NextResponse } from "next/server";
import { authClient, saveSession } from "@/lib/auth";
import { allowedUser, isDemo } from "@/lib/config";
export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export async function GET(req: NextRequest) {
  const destination = new URL("/", req.url);
  const code = req.nextUrl.searchParams.get("code");
  if (!code || isDemo()) {
    destination.searchParams.set("auth_error", "invalid_link");
    return NextResponse.redirect(destination);
  }
  try {
    const client = authClient();
    const { data, error } = await client.auth.exchangeCodeForSession(code);
    if (error || !data.session || !data.user || !allowedUser(data.user.id)) {
      destination.searchParams.set("auth_error", "not_authorized");
      return NextResponse.redirect(destination);
    }
    await saveSession(data.session.access_token, data.session.refresh_token, data.session.expires_in);
    return NextResponse.redirect(destination);
  } catch {
    destination.searchParams.set("auth_error", "unavailable");
    return NextResponse.redirect(destination);
  }
}
