# AXXIBOTS HQ

A private, read-only operations cockpit for an autonomous AI business. Next.js 16, TypeScript, Tailwind 4, lightweight SVG office, Supabase Auth and a server-side PostgreSQL connection. No paid analytics or animation services; no AI calls are made by HQ.

## Run locally

Requires Node 22 or newer.

```sh
npm ci
cp .env.example .env.local
npm run dev
```

Open http://localhost:3000. The example starts in **DEMO MODE**: all displayed records and financial amounts are synthetic. Production snapshots are never committed. A live connection failure never falls back to demo.

```sh
npm run typecheck
npm test
npm run build
```

## Deploy to Vercel

1. Import `axxent-UG/axxibots` in Vercel. Framework: **Next.js**. Root directory: repository root. Install: `npm ci`. Build: `npm run build`. Node: 22 or 24.
2. For a safe initial visual deployment, set `DEMO_MODE=true`. No database credentials are required. The demo banner remains visible everywhere.
3. For private live data, set the server environment variables listed below in Vercel's project settings. Set `DEMO_MODE=false` and redeploy. Use Production scope; use separate test credentials or demo mode for Preview deployments.
4. Use an existing Supabase Auth email/password user (or invite one in the Supabase dashboard). Put the exact user UUID in `HQ_ALLOWED_USER_IDS`. An authenticated but unlisted user cannot access HQ business data. There is no public signup route.
5. Sign in on the deployed site. Verify LIVE MODE, inspect a known task, compare a cost entry, then check refreshing. If live setup is incomplete, the app fails closed and shows a configuration/connection error.
6. For recovery, set `DEMO_MODE=true` and redeploy to show only synthetic data. Do not weaken authentication or certificate verification.

Enter secrets **only in Vercel or a local untracked `.env.local`**, never in chat or the repository. The deployment is not performed automatically by this implementation.

### Environment variables

| Variable                   | Required               | Purpose                                                                                                                                            |
| -------------------------- | ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DEMO_MODE`                | Recommended explicitly | `true` for synthetic demo; `false` for private live mode. If absent, demo is chosen only when both database URL and auth key are absent.           |
| `SUPABASE_URL`             | Live                   | `https://xhztnnhrcqwuooezcbgh.supabase.co`                                                                                                         |
| `SUPABASE_PUBLISHABLE_KEY` | Live                   | Publishable key for Supabase Auth; stored server-side. A legacy anon key also works. No service-role key is needed.                                |
| `HQ_ALLOWED_USER_IDS`      | Live                   | Comma-separated Supabase Auth UUIDs. An empty list denies all users.                                                                               |
| `DATABASE_URL`             | Live                   | Supabase **transaction pooler** connection string, normally port 6543, entered privately. Prefer an existing account with SELECT-only permissions. |
| `DATABASE_CA_CERT`         | Only if needed         | PEM CA certificate for the pooler. TLS certificate verification is always enabled.                                                                 |

No `NEXT_PUBLIC_*` secrets. If the connection URL contains `sslmode=require`, the application removes that flag before configuring pg so it cannot silently disable certificate validation. No named/prepared statements are used with the transaction pooler.

## Features

- Seven-department isometric office, individual desks and lightweight animated agents. Workstations support mouse and keyboard inspection. No agent is shown working just because its registry is active.
- Office, operations, pipeline, finance and agent-performance views; responsive navigation, search, filters, detail inspector and reduced-motion support.
- Automatic 20-second refresh while visible; refresh on return; overlapping requests prevented. Errors retain a marked stale snapshot and pause work animations. Unauthorized sessions clear displayed private data.
- Monitor execution timing, n8n status, separate evidence-based business outcome, errors, task attempts, current workload, bottlenecks and potentially stalled tasks.
- Pipeline deduplicates materialized products and ideas; uses actual statuses and listing/sales evidence. Unknown statuses are visible in Unmapped. Product history shows linked task records and timestamps.
- Actual and estimated API costs for today/7/30 days, all-history costs per agent/product, 30-day trend, expenses, gross revenue and estimated ledger surplus. Unknown costs and credit balances remain explicit.
- Agent completion counts, business success rate, known/unknown outcome counts, workload, recorded review pass rate, cost and recent activity.

## Security and operating model

Private business records are returned only by authenticated `/api/data` requests after Supabase `getUser` verification and a server-side UUID allowlist. Session cookies are HttpOnly, Secure in production, SameSite=Lax; sessions refresh server-side. Login uses existing Supabase password auth and its configured rate limits. Logout clears HQ cookies. Mutating auth requests enforce same origin. Responses are private and no-store. The page itself includes no private data in its initial HTML.

Data reads use a certificate-verified server-side pg connection. Every snapshot uses one `REPEATABLE READ READ ONLY` transaction and fixed SELECT projections against the inspected schema. No generic SQL endpoint, writes, migrations, workflow triggers or public live-record endpoints exist. Raw prompts, payloads, sale customer details and storage paths are not exported. Error displays redact sensitive keys, tokens and URLs; database errors are not echoed to the browser. A service-role key is not required or supported.

An existing SELECT-only database account adds defense in depth. This code creates no account and changes no tables, RLS policies, grants or n8n workflows. Direct PostgreSQL access also avoids having to expose `axx` through the public Data API.

Supabase inspection was read-only on 11 Oct 2026. See [data semantics](docs/DATA_SEMANTICS.md) for mappings and confidence limits.

## Files

| Files                                                                                                        | Responsibility                                                                 |
| ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| `app/page.tsx`, `app/layout.tsx`, `app/globals.css`                                                          | Application shell, metadata and responsive Tailwind/CSS styling                |
| `components/office.tsx`                                                                                      | SVG architecture, workstations, characters and evidence-dependent animation    |
| `components/cockpit.tsx`                                                                                     | Dashboard views, finance chart, polling, login and record inspector            |
| `app/api/data/route.ts`, `app/api/auth/route.ts`                                                             | Protected snapshot, sign-in/sign-out handlers                                  |
| `lib/auth.ts`, `lib/config.ts`, `lib/data.ts`                                                                | Server-only authentication, environment policy and read-only SQL access        |
| `lib/model.ts`, `lib/demo.ts`                                                                                | Data derivation and clearly synthetic fixtures                                 |
| `tests/model.test.ts`                                                                                        | Outcome, state, pipeline, accounting, calendar and redaction regression checks |
| `.env.example`, `next.config.ts`, `postcss.config.mjs`, `tsconfig.json`, `package.json`, `package-lock.json` | Deployment and pinned dependencies                                             |
| `.github/workflows/check.yml`                                                                                | Automated typecheck, tests and production build                                |

## Validation and known limitations

- Typecheck passed; production build passed; 13 regression tests passed; production dependency audit found no vulnerabilities at implementation time.
- All nine SELECT projections were checked through the connected Supabase SQL tool against the actual schema, without changes. Sample source shapes and enum values were inspected. This validates schema compatibility, **not** the deployed connection/auth flow.
- Office SVG was rendered and visually inspected; React render warnings were corrected. Browser interaction, mobile visual QA and live Vercel authentication/database integration could not be run in this environment. Validate them after private configuration.
- Polling is near real time, not a push connection. Status comes from recorded evidence, not a machine heartbeat. A one-hour stale-run heuristic can flag legitimate long jobs.
- Data snapshots are limited to 10,000 rows per source table. If a source exceeds this, the endpoint errors instead of silently truncating totals. A paginated/aggregate read layer will be needed as the business grows.
- Business outcomes can be UNKNOWN when completion evidence is absent or old task results have been overwritten. The source database has no assumed universal transition-history table.
- Financial totals are based on available records; missing costs cannot be inferred. Ledger surplus is not audited profit. Actual billed API balances, subscription credits, taxes and comprehensive refunds are not integrated. Run estimates deduplicate by `run_id`; unlinked duplicates cannot be identified automatically.
- Per-agent cost attribution requires an expense `run_id` that matches a workflow run. Missing attribution is grouped as Unattributed. No invented cost allocation.
- Output quality is calculated only from ACCEPTED/REVISION_REQUESTED/REJECTED task reviews. No overall autonomy or quality score is invented; 90% figures are targets.
- `is_test` ideas/products/listings are excluded; tasks and runs have no dedicated `is_test` column and include recorded execution history.
- Desk layouts support the existing registry. Very large future departments may need expanded room geometry.
