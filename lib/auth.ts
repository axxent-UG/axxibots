import "server-only";
import { createClient } from "@supabase/supabase-js";
import { cookies } from "next/headers";
import { allowedUser } from "./config";
export function authClient() {
  const url = process.env.SUPABASE_URL,
    key = process.env.SUPABASE_PUBLISHABLE_KEY;
  if (!url || !key) throw new Error("Authentication is not configured");
  return createClient(url, key, {
    auth: {
      persistSession: false,
      autoRefreshToken: false,
      detectSessionInUrl: false,
    },
  });
}
export async function saveSession(
  access: string,
  refresh: string,
  expires: number,
) {
  const jar = await cookies(),
    options = {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax" as const,
      path: "/",
    };
  jar.set("hq-access", access, { ...options, maxAge: expires });
  jar.set("hq-refresh", refresh, { ...options, maxAge: 7 * 86400 });
}
export async function clearSession() {
  const jar = await cookies();
  jar.delete("hq-access");
  jar.delete("hq-refresh");
}
export async function authorize() {
  const jar = await cookies(),
    client = authClient();
  let access = jar.get("hq-access")?.value;
  let user = access ? (await client.auth.getUser(access)).data.user : null;
  if (!user) {
    const refresh = jar.get("hq-refresh")?.value;
    if (!refresh) return false;
    const result = await client.auth.refreshSession({ refresh_token: refresh });
    if (result.error || !result.data.session) return false;
    access = result.data.session.access_token;
    user = (await client.auth.getUser(access)).data.user;
    if (user && allowedUser(user.id))
      await saveSession(
        access,
        result.data.session.refresh_token,
        result.data.session.expires_in,
      );
  }
  return !!user && allowedUser(user.id);
}
