import { NextResponse, type NextRequest } from "next/server";
import { requireSiteAccess } from "./lib/access";

// Protect the whole website, including demo pages, API routes and assets.
// API handlers also validate access independently as defense in depth.
export function proxy(request: NextRequest) {
  const denied = requireSiteAccess(request);
  if (denied) return denied;
  const response = NextResponse.next();
  response.headers.set("Cache-Control", "private, no-store, max-age=0");
  response.headers.set("Vary", "Authorization, Cookie");
  return response;
}
export const config = { matcher: "/:path*" };
