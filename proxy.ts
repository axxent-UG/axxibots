import { NextResponse, type NextRequest } from "next/server";

// The single HQ sign-in is Supabase Auth. API routes verify the authenticated
// user against HQ_ALLOWED_USER_IDS; no browser HTTP Basic Auth challenge.
export function proxy(_request: NextRequest) {
  const response = NextResponse.next();
  response.headers.set("Cache-Control", "private, no-store, max-age=0");
  response.headers.set("X-Content-Type-Options", "nosniff");
  return response;
}
export const config = { matcher: "/:path*" };
