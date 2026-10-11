# Source data and display semantics

Schema inspected read-only: Supabase `xhztnnhrcqwuooezcbgh`, schema `axx`, 11 Oct 2026. No production rows are saved in this repository. Queries are fixed projections in `lib/data.ts` and were validated against the current columns.

## Sources

| Source           | Used for                                                                                                 |
| ---------------- | -------------------------------------------------------------------------------------------------------- |
| `agent_registry` | Agent names, role, administrative status and optional monthly estimate                                   |
| `agents`         | Agent identity, administrative status and `is_active`; merged by `id = agent_id`                         |
| `workflow_runs`  | Execution IDs, agent, run status, start/finish/update, run cost estimate and selected outcome signals    |
| `tasks`          | Task status, assigned agent, attempts, reviews, timestamps, product links, selected result/error signals |
| `product_ideas`  | Ideas, owner decision, title, lifecycle status and timestamps                                            |
| `products`       | Materialized products linked by `product_idea_id`; title/status/compliance and timestamps                |
| `listings`       | Etsy state and listing creation attempts/errors, linked by `product_id`                                  |
| `expenses`       | EUR amounts, `is_estimate`, date, category, run and product attribution                                  |
| `sales`          | Gross recorded EUR revenue and product/listing links; customer/raw records are not selected              |

## Agent state

Precedence: planned/paused/retired or inactive → OFFLINE; fresh IN_PROGRESS task/RUNNING run → WORKING; BLOCKED task → BLOCKED; unresolved FAILED task → ERROR; stale running evidence → BLOCKED; latest failed outcome → ERROR; otherwise IDLE. Fresh means last evidence within 60 minutes. IDLE means no evidence of current work; OFFLINE reflects administrative configuration, not a failed heartbeat.

Departments are presentation assignments based on recorded agent IDs: CEO/report/approvals in Management; research/trends in Research; product/compliance in Product Management; design in Design Studio; Etsy in Etsy Operations; analytics/finance in Finance; remaining agents in Infrastructure. Roles and identities remain the real registry values.

## Business outcome

Task-to-run links consider `tasks.run_id`, `tasks.result.run_id` and `tasks.last_error.run_id`. FAILED task or explicit failed output/QA status overrides workflow SUCCESS. BLOCKED task yields BLOCKED; running evidence yields IN PROGRESS; FAILED/STOPPED_LIMIT run yields FAILED. All linked tasks DONE confirms SUCCESS. Technical SUCCESS alone yields UNKNOWN.

Task results are mutable. Earlier run outcomes may become UNKNOWN after later retries overwrite evidence. No historical completion is fabricated. A database error is distinct from a failed business run: it makes the whole displayed snapshot unavailable/stale.

## Pipeline

| Actual evidence                             | Display stage                           |
| ------------------------------------------- | --------------------------------------- |
| ARCHIVED / REJECTED                         | INACTIVE                                |
| Linked sales                                | SALES                                   |
| Active Etsy listing or PUBLISHED            | PUBLISHED                               |
| Draft Etsy listing or DRAFT                 | ETSY DRAFT                              |
| AWAITING_APPROVAL or pending owner decision | APPROVAL                                |
| DESIGNING / APPROVED                        | DESIGN                                  |
| DESIGNED / COMPLIANCE_REVIEW                | QUALITY CONTROL                         |
| RESEARCHED                                  | APPROVAL, or DESIGN when owner approved |
| IDEA                                        | RESEARCH, or DESIGN when owner approved |
| Anything else                               | UNMAPPED                                |

A materialized product replaces its linked idea in the board. Current record timestamps and linked tasks are displayed as history; they are not presented as a complete sequence of status transitions. Failed/blocked linked tasks flag a product for inspection.

## Finance

`expenses` is canonical. `is_estimate=false` is ACTUAL COST; true is ESTIMATED COST; null/unrecognized basis is UNKNOWN. Missing amount is UNKNOWN even if a basis flag exists. Workflow `est_ai_cost_eur` is fallback evidence only when no `ai_api` expense references that run. Multiple expense components of a run are summed; the run estimate is not added on top.

Daily windows use Europe/Berlin calendar days, including DST changes. Today is one day; 7/30 days include today and preceding calendar days. Date-only expense values are preserved. Future-dated entries are excluded from the dated windows/trend. All-history ledger tables reflect all recorded entries.

Estimated ledger surplus = gross recorded revenue − actual ledger expenses − estimated ledger expenses. Unknown expense amounts/basis or revenue makes surplus UNKNOWN. This calculation deliberately does not subtract `sales` fee/cost fields a second time because the same amounts may already exist in expenses. It can therefore overstate real profitability when those costs are not logged. See it as an estimate of the recorded ledger, not net business profit. API credit balance is always UNKNOWN without a billing integration.

Cost by product uses recorded `product_id` / `product_idea_id`; product inspection lists both attributed records. Cost by agent joins expense `run_id` to run `agent_id`. Missing links stay Unattributed.

## Performance

Completed = tasks with DONE. Workload = PENDING + IN_PROGRESS + BLOCKED. Business success = confirmed SUCCESS / (confirmed SUCCESS + FAILED); unknown and blocked outcomes are separately excluded. Quality = ACCEPTED / (ACCEPTED + REVISION_REQUESTED + REJECTED) task reviews, UNKNOWN without such reviews. These are recorded outcomes, not an invented assessment of commercial quality or autonomy.
