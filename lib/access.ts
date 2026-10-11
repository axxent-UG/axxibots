import { createHash, timingSafeEqual } from "node:crypto";
import { NextResponse, type NextRequest } from "next/server";

export type AccessDecision = "authorized" | "unauthorized" | "unconfigured";

// All inputs remain server-side. Compare fixed-length digests to avoid leaking
// password or username length through the credential comparison.
export function accessDecision(
  authorization: string | null,
  password: string | undefined,
  username = "alex",
): AccessDecision {
  if (
    !password ||
    password.length < 16 ||
    password.length > 1024 ||
    !username ||
    username.length > 80 ||
    username.includes(":")
  ) {
    return "unconfigured";
  }
  if (!authorization || authorization.length > 8192) return "unauthorized";
  const match = /^Basic ([A-Za-z0-9+/]+={0,2})$/i.exec(authorization);
  if (!match) return "unauthorized";
  const credentials = Buffer.from(match[1], "base64").toString("utf8");
  const separator = credentials.indexOf(":");
  if (separator < 0) return "unauthorized";
  const actual = `${credentials.slice(0, separator)}\0${credentials.slice(separator + 1)}`;
  const expected = `${username}\0${password}`;
  const hash = (value: string) => createHash("sha256").update(value).digest();
  return timingSafeEqual(hash(actual), hash(expected))
    ? "authorized"
    : "unauthorized";
}

export function requireSiteAccess(request: NextRequest): NextResponse | null {
  const decision = accessDecision(
    request.headers.get("authorization"),
    process.env.HQ_ACCESS_PASSWORD,
    process.env.HQ_ACCESS_USER ?? "alex",
  );
  if (decision === "authorized") return null;
  const headers = {
    "Cache-Control": "private, no-store, max-age=0",
    Vary: "Authorization, Cookie",
    "X-Content-Type-Options": "nosniff",
    ...(decision === "unauthorized"
      ? {
          "WWW-Authenticate": 'Basic realm="AXXIBOTS HQ", charset="UTF-8"',
        }
      : {}),
  };
  return NextResponse.json(
    {
      kind: "SITE_ACCESS",
      error:
        decision === "unconfigured"
          ? "HQ access is locked. Configure HQ_ACCESS_PASSWORD (at least 16 characters) in the hosting environment."
          : "Site password access was rejected. Reload this page to sign in again.",
    },
    { status: decision === "unconfigured" ? 503 : 401, headers },
  );
}
