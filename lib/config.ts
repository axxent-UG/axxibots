import "server-only";
export function isDemo() {
  if (process.env.DEMO_MODE !== undefined)
    return process.env.DEMO_MODE === "true";
  return !process.env.DATABASE_URL && !process.env.SUPABASE_PUBLISHABLE_KEY;
}
export function allowedUser(id: string) {
  return (process.env.HQ_ALLOWED_USER_IDS ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean)
    .includes(id);
}
