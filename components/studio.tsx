"use client";
import { useCallback, useEffect, useState } from "react";
import { studioStages, type Studio, type StudioProduct } from "@/lib/studio";

const eur = (v: number | null | undefined) =>
  v == null
    ? "—"
    : new Intl.NumberFormat("en", { style: "currency", currency: "EUR", minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(v));
const when = (v: string | null) =>
  v
    ? new Intl.DateTimeFormat("en-GB", { timeZone: "Europe/Berlin", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(v))
    : "—";
const stageLabel = (s: string) => studioStages.find(([k]) => k === s)?.[1] ?? s;
const tone = (s: string) =>
  s === "draft" ? "success" : s === "qa" ? "awaiting-owner" : s === "art" || s === "assembling" ? "working" : "running";
const etsyEdit = (id: number) => `https://www.etsy.com/your/shops/me/listing-editor/edit/${id}`;

function Gauge({ label, used, cap }: { label: string; used: number; cap: number | null }) {
  const share = cap ? Math.min(100, Math.round((Number(used) / Number(cap)) * 100)) : 0;
  return (
    <div className="metric">
      <span className="eyebrow">{label}</span>
      <strong>{eur(used)}</strong>
      <div style={{ height: 6, borderRadius: 3, background: "#283747", margin: "10px 0 6px" }}>
        <div style={{ width: `${share}%`, height: 6, borderRadius: 3, background: share > 85 ? "#edbd77" : "#99dfbd" }} />
      </div>
      <small className="muted">{cap == null ? "No cap set" : `of ${eur(cap)} cap · ${share}%`}</small>
    </div>
  );
}

export default function StudioView({ demo }: { demo: boolean }) {
  const [data, setData] = useState<Studio | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState("");

  const load = useCallback(async () => {
    try {
      const r = await fetch("/api/studio", { cache: "no-store" });
      const body = await r.json();
      if (!r.ok) throw new Error(body.error ?? "Studio data unavailable.");
      setData(body);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Studio data unavailable.");
    }
  }, []);
  useEffect(() => {
    void load();
    const t = setInterval(() => document.visibilityState === "visible" && void load(), 20000);
    return () => clearInterval(t);
  }, [load]);

  const act = async (action: "release" | "archive_legacy", question: string) => {
    if (!window.confirm(question)) return;
    setBusy(action);
    setNote("");
    try {
      const r = await fetch("/api/owner/studio", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ action }) });
      const body = await r.json();
      if (!r.ok) throw new Error(body.error ?? "Action failed.");
      const res = body.result ?? {};
      setNote(
        action === "release"
          ? `${res.released ?? 0} product(s) released. The listing agent turns them into Etsy drafts on its next run.`
          : `Archived ${res.decisions ?? 0} decisions, ${res.org_proposals ?? 0} org proposals and ${res.tasks ?? 0} tasks from the old briefing.`,
      );
      await load();
    } catch (e) {
      setNote(e instanceof Error ? e.message : "Action failed.");
    } finally {
      setBusy(null);
    }
  };

  if (!data)
    return (
      <div className="panel connection">
        <span className="eyebrow">{error ? "UNAVAILABLE" : "LOADING"}</span>
        <h2>{error || "Opening the studio…"}</h2>
        {error && <button className="button" onClick={() => void load()}>Retry</button>}
      </div>
    );

  const products = data.products.filter((p) => p.status !== "art");
  const artKits = data.products.filter((p) => p.status === "art" || p.assets_total > 0);
  const waiting = products.filter((p) => p.status === "qa");
  const drafts = products.filter((p) => p.status === "draft");
  const moving = products.filter((p) => ["ready", "listing", "assembling"].includes(p.status));
  const collections = Array.from(new Set(data.products.map((p) => p.collection ?? "Unsorted")));
  const legacyTotal = data.legacy.decisions_pending + data.legacy.org_proposals_open + data.legacy.tasks_open;

  return (
    <>
      <div className="metrics">
        <div className="metric">
          <span className="eyebrow">Etsy drafts to publish</span>
          <strong>{drafts.length}</strong>
          <small className="muted">You publish them in Etsy. Agents never do.</small>
        </div>
        <div className="metric">
          <span className="eyebrow">Waiting for your release</span>
          <strong>{waiting.length}</strong>
          {waiting.length > 0 && !demo ? (
            <button className="button" style={{ marginTop: 8 }} disabled={!!busy} onClick={() => void act("release", `Release ${waiting.length} finished product(s) to the listing agent? It creates Etsy DRAFTS only (no publishing). Prices: ${waiting.map((p) => `${p.title} ${eur(p.price_eur)}`).join(", ")}`)}>
              {busy === "release" ? "Releasing…" : "Release to listing agent"}
            </button>
          ) : (
            <small className="muted">{moving.length} on the way to Etsy</small>
          )}
        </div>
        <Gauge label="AI spend today" used={data.budget.today_eur} cap={data.budget.day_cap_eur} />
        <Gauge label="AI spend this month" used={data.budget.month_eur} cap={data.budget.month_cap_eur} />
      </div>
      {(note || error) && <div className="notice" role="status"><span>i</span><div>{note || error}</div></div>}

      <section className="panel" style={{ marginTop: 20 }}>
        <div className="panel-head">
          <div><span className="eyebrow">HOW A PRODUCT IS MADE</span><h2>Inkwell Ephemera production line</h2></div>
        </div>
        <p className="small muted" style={{ lineHeight: 1.7 }}>
          1 Illustrations agent paints the motifs → 2 kit engine assembles pages, PDFs, JPG ZIP and listing images →
          3 <strong>you release</strong> (button above) → 4 listing agent writes title, tags and description and creates the
          Etsy draft in the right section → 5 <strong>you publish</strong> in Etsy.
        </p>
      </section>

      {collections.map((c) => {
        const rows = products.filter((p) => (p.collection ?? "Unsorted") === c);
        const art = artKits.filter((p) => (p.collection ?? "Unsorted") === c).reduce((s, p) => s + Number(p.art_eur || 0), 0);
        const artAssets = artKits.filter((p) => (p.collection ?? "Unsorted") === c).reduce((s, p) => s + p.assets_done, 0);
        return (
          <section className="panel" style={{ marginTop: 20 }} key={c}>
            <div className="panel-head">
              <div>
                <span className="eyebrow">COLLECTION</span>
                <h2>{c}</h2>
              </div>
              <span className="small muted">
                {rows.filter((p) => p.status === "draft").length}/{rows.length} drafts · {artAssets} illustrations · art cost {eur(art)}
              </span>
            </div>
            {rows.length === 0 ? (
              <p className="small muted">Illustrations in progress. Products appear here once the kit engine has assembled them.</p>
            ) : (
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr><th>Product</th><th>Status</th><th>Price</th><th>Etsy section</th><th>Files</th><th>Etsy</th></tr>
                  </thead>
                  <tbody>
                    {rows.map((p: StudioProduct) => (
                      <tr key={p.slug}>
                        <td>{p.title}<br /><small className="muted">{p.product_type ?? "Ephemera Kit"} · updated {when(p.updated_at)}</small></td>
                        <td><span className={`badge ${tone(p.status)}`}>{stageLabel(p.status)}</span>{p.error && <><br /><small className="negative">{p.error.slice(0, 140)}</small></>}</td>
                        <td>{eur(p.price_eur)}</td>
                        <td>{p.section ?? "—"}</td>
                        <td><small>{p.downloads} downloads · {p.images} images</small></td>
                        <td>{p.etsy_listing_id && !demo ? <a className="table-link" href={etsyEdit(p.etsy_listing_id)} target="_blank" rel="noreferrer">Open draft ↗</a> : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        );
      })}

      <section className="panel" style={{ marginTop: 20 }}>
        <div className="panel-head">
          <div><span className="eyebrow">OLD BRIEFING</span><h2>Backlog from the previous strategy</h2></div>
        </div>
        <p className="small muted">
          Before the Inkwell Ephemera pivot the CEO agent proposed party games, planners and spreadsheet products. These items are
          still open: {data.legacy.decisions_pending} CEO decisions, {data.legacy.org_proposals_open} organisation proposals and{" "}
          {data.legacy.tasks_open} queued or blocked tasks. Open tasks keep waking the old dispatcher. Archiving marks them
          expired / withdrawn / cancelled; nothing is deleted and everything stays in the audit log.
        </p>
        {legacyTotal > 0 && !demo && (
          <button className="button subtle" disabled={!!busy} onClick={() => void act("archive_legacy", `Archive ${legacyTotal} open items from the old briefing? Nothing is deleted.`)}>
            {busy === "archive_legacy" ? "Archiving…" : "Archive old-briefing backlog"}
          </button>
        )}
        {legacyTotal === 0 && <p className="small">Nothing open. The backlog is clean.</p>}
      </section>
    </>
  );
}
