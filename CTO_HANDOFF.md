# AXXIBOTS technical handoff

Updated 2026-10-11. Start here, then verify current production before changing it.
This repository is public: keep customer data, business figures, production payloads,
credentials and confidential decision records out of commits. The detailed private
audit is in `axx.reports`, type `cto_reliability_sprint_20261011`.

## Architecture and existing capabilities

- n8n orchestrates the established agents; Supabase schema `axx` holds business state,
  tasks, decisions, registry, budgets, immutable audit events and operational reports.
- `axx.agent_registry` is a view over existing agent/run records. Do not create a
  second registry. Its free-text notes can be stale even when counters are current.
- `AXXIBOTS_00_DISPATCHER` runs every 30 minutes. `axx.dispatch_tick` claims and settles
  route tasks with deduplication, busy checks, bounded attempts and escalation holds.
  `axx.detect_stalls` already exists; do not implement another stall detector.
- Enabled routes cover Etsy reconciliation/drafting, compliance, CEO product review,
  product packaging and printable design. Research has its own schedules; an n8n
  subworkflow trigger does not mean a dispatcher route is enabled.
- Research uses general web evidence, deterministic evidence vectors, commercial
  similarity/novelty checks, qualification and bounded research queues. Weekly market
  signals and daily retries exist. The former coarse keyword filter was replaced.
- Printable design has plan/write/render phases and deterministic checks. Its current
  renderer supports party-game layouts; other formats need scoped shared capabilities.
  The earlier size-aware listing-image correction and completed-asset reconciliation
  were verified and preserved. Historical failures are not evidence they remain broken.
- Product Manager creates product specs and packages private assets through the
  `product-package` Edge Function. **New specs use an AI model; repair packaging is free.**
- Compliance and CEO review precede human approval. Etsy Manager creates drafts only;
  reconciliation handles uncertain create attempts. The proxy blocks publication and
  database triggers retain the owner approval gates.
- Rendering/packaging Edge Functions use one-use nonces. Existing access controls,
  credentials, publication rules and spending limits were not changed in this sprint.
- Scheduled listing performance snapshots exist. Receipt/revenue analytics, the daily
  report workflow and the general CEO workflow remain manually triggered.
- CEO organizational and portfolio SQL reviews already exist. Organizational proposals
  are evidence-based records; they do not automatically deploy new agents.
- HQ is this Next.js app: read-only server-side SQL, a required site password,
  additional allowlisted Supabase authentication for live records, and explicit demo mode.
  See `README.md` and `docs/DATA_SEMANTICS.md` for established behavior.

## Completed in this sprint

1. **Package completion:** only the requested product, matching run, persisted package
   path, positive byte count and matching HTTP response can advance to compliance.
   HTTP 200 alone is insufficient. Failed checks mark the run FAILED so the existing
   dispatcher retry policy can act. Replays do not duplicate the handoff audit event.
2. **Spec accounting:** record token usage and an idempotent expense immediately after
   the model response, before parsing/validation. Run records now receive the estimate
   used by budget checks. Missing usage stops product creation and is explicit in the
   run input. Historical zero-valued PM runs were reconciled from existing ledger rows,
   with an audit event; no historical tokens were invented and no expenses duplicated.
3. **PM admission:** new AI specs require the existing global daily and monthly budgets
   to allow work. Missing budget evidence fails closed. Free repairs remain possible;
   kill-switch and agent-status checks still take precedence. No limits were raised.
4. **Research completion:** save results/costs while the run remains RUNNING; mark success
   only after promotion, scoring and qualification finish and at least one task completed.
   A downstream failure marks the same run FAILED while retaining findings and costs.
   One independently verified historical execution mismatch was audited and corrected.
5. **HQ pipeline:** normalize owner-decision case so production `APPROVED` values route
   eligible ideas to Design rather than remaining in Research/Approval.

Dispatcher production logic was preserved. An inspected error-log node was already
correct; its draft was restored to the original graph and was not published as a fix.

## Source and deployment state

| Component | Source | Production state / rollback |
| --- | --- | --- |
| Product Manager | `ops/product-manager/*.sql`, `decide-path.js`, `validate-spec.js` | Published version `e4920b1c-d51f-4be7-9b45-12a59878587a`; preceding version `f2df3d5c-df3b-4012-afb1-90ccbb1495c5` |
| Market Research | `ops/research/*.sql` | Published version `356810d9-6ccd-4a3e-b2ad-ab70d692d4de`; preceding version `8881fd7e-55ca-4459-9316-2008ac6c1d11` |
| HQ decision mapping | `lib/model.ts`, `tests/model.test.ts` | Source fixed and locally verified; deployed revision not verified because Vercel team-scope access returned 403 |

These SQL files are n8n node queries, **not schema migrations**. Do not run the pickup
query casually: it creates operational run state. No schema or grants changed.

PM wiring: Write Product Spec -> Record Spec Usage -> Validate and Package Spec.
The validator reads the original model response by node name. Usage, model-validation
and package-transport errors route to Log PM Failure. Hand Over to Compliance receives
the expected product ID from the original new/repair branch, not from the response.
Research wiring: Finish Run and Verify (records RUNNING results) -> Promote Discoveries
-> Rescore Opportunities -> Confirm Research Completion. Both post-processing nodes
have an error output to Log Finalization Failure.

## Verification

- 26 local tests passed; TypeScript check passed; production build passed.
- `node scripts/build-pm-sql-test.mjs` generates a single-connection PostgreSQL test
  script using TEMP tables only. It passed against PostgreSQL: 11 package scenarios,
  3 research outcomes, replay protection, expense deduplication and missing usage.
  All fixture writes were rolled back. Requires the existing `axx` enum types.
- The PM pickup SQL was planned with EXPLAIN without executing writes.
- n8n PM smoke execution `372` succeeded, selected no work and made no model call.
- Published workflow graphs/queries were read back. This is **not** a full live
  product-production test; the first real runs through changed branches still need review.
- Existing site-password tests passed. No private HQ browser session was available for
  a fresh authenticated end-to-end check. Vercel's metadata endpoint worked, but scoped
  deployment listing returned 403; no authenticated CLI fallback was installed.

## Prioritized backlog

1. Review the next real PM and Research runs: confirm artifacts, handoff states, cost
   entries and terminal statuses agree. Do not create paid work just to get a green test.
2. Audit research failure-cost accounting and execution correlation: released attempts
   still use estimates without a run link; the global error handler creates separate
   failure rows rather than always closing the original run. Preserve audit history.
3. Resolve design-limit semantics (component rows versus products) and add safe budget
   reservations if needed. Current admission checks are estimated thresholds, not atomic
   provider billing caps; concurrent work can overshoot remaining headroom.
4. Restore Vercel team access and verify the deployed HQ revision and authenticated
   live-data path. Do not change passwords, protection or auth rules to work around this.
5. Refresh stale registry narratives and blocker records from verified owner decisions.
   Do not re-request already recorded approvals or reinterpret an old blocker as current.
6. Improve independent visual/usability QA, source-backed commercial evidence and
   product differentiation. Technical PDF validity and model scores are not proof of
   commercial quality. Keep publication and strategy decisions with the owner.
7. Expand receipts analytics/report scheduling when commercially needed, using the
   existing workflows. Broader business expansion remains a later strategic decision.

Measure eligible task completion and independently reviewed quality with explicit
denominators. Do not substitute n8n transport success or invented scores for outcomes.
