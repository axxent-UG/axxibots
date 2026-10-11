import "server-only";
import { cookies } from "next/headers";
import { authorize } from "./auth";
import { buildSnapshot, type Raw } from "./model";

export async function authorizedRpc(functionName: "axx_hq_snapshot" | "axx_hq_owner_decision", payload: Record<string, unknown> = {}) {
  if (!(await authorize())) throw new Error("HQ_UNAUTHORIZED");
  const token = (await cookies()).get("hq-access")?.value;
  if (!token) throw new Error("HQ_SESSION_MISSING");
  const base = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_PUBLISHABLE_KEY;
  if (!base || !key) throw new Error("HQ_SUPABASE_CONFIG");
  const response = await fetch(`${base}/rest/v1/rpc/${functionName}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", apikey: key, Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
    cache: "no-store",
    signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) {
    const category = response.status === 401 || response.status === 403 ? "HQ_RPC_AUTH" : response.status === 404 ? "HQ_RPC_NOT_FOUND" : "HQ_RPC_FAILED";
    console.error("HQ_RPC_DIAGNOSTIC", { category, status: response.status, functionName });
    throw new Error(category);
  }
  return response.json();
}

export async function liveSnapshotViaRpc() {
  const raw = await authorizedRpc("axx_hq_snapshot") as Raw;
  return buildSnapshot(raw, "LIVE");
}
