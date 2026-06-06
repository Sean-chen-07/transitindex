# Backend restructure — brief for a fresh session

> **Status:** Proposed (2026-06-06). Not started. Paste the body below into a new
> session (or have that session read this file) to kick off the backend data-model
> restructure. The DB is **PostgreSQL** (not MySQL).

Restructure the TransitIndex **backend** — the data model itself, not the web app.
Metrics are stored flat and one-directional right now, and the next push is scanning
PDFs + building an FOI workflow, so the metric system needs to be precise and properly
linked first. Four goals:

## 1. Make metrics a linked equation graph (bidirectional derivation)
Today derived metrics (farebox, cost/rider, etc.) only compute one way from fixed
inputs. Build a relationship/constraint system where, for a given **agency + period +
scope**, any unknown value can be **solved** from the others. Example:
`farebox_recovery = revenue ÷ expenses`, so given farebox + revenue, back out expenses.
Same for `total_subsidy = expenses − revenue`, `expenses ≈ labour + energy + materials`,
`average_fare = revenue ÷ ridership`, etc. Propagate to a fixpoint.

Every solved value is marked **derived**, carries **provenance** (which equation + which
inputs), and is **exact arithmetic on same-period values only** — never fabricated or
estimated (respect the "every number is dispute-proof / nothing estimated" invariant).
When a value is **both** sourced and derivable, cross-check them (reuse the existing
`sum_mismatch` / `cross_source_disagreement` flags) — a trust feature. Decide how the
graph handles **over-determination / conflicts**.

## 2. Kill the monthly-vs-annual duplication; roll up by period
Separate `monthly_ridership` and `annual_ridership` metric codes are wrong. One
ridership metric, with values at different **period granularities** (monthly / quarterly
/ annual); `annual = Σ(12 months)` when all 12 are present (flag or skip if incomplete;
reuse carry-forward rules). Period is the **dimension**, not baked into the metric code.
Apply the same to anything else that's period-duplicated. Ranking must still compare
**same-granularity, same-period** — don't break the existing period + scope rank rules.

## 3. Write a precise per-metric data dictionary (the real point)
For PDF extraction + FOIs, each metric needs an exact spec: what it **IS**, what it is
**NOT**, unit, period semantics, included/excluded, **EN + FR** label/synonym variants
as they appear in annual reports, where in a typical report it lives, common confusions
(unlinked vs linked trips; operating revenue vs total revenue incl. subsidy; a metro car
vs a bus in "fleet"), source tier (StatCan / annual report / FOI), and the equations it
participates in. This dictionary must drive **both** the PDF-extraction prompts **and**
the FOI request templates.

## 4. Restructure both the database and the Excel workbook to match
- **DB (PostgreSQL):** schema in `db/migrations` (Lane 0) + `db/seeds`; the metric
  catalog is `db/seeds/04_metrics.sql` and `ingest/transitindex_ingest/refdata.py`
  (keep them in parity). The web app only **reads** the schema (`web/src/server/...`) —
  do not break the read layer or the paywall (raw values stay server-only, ranks free).
- **Excel workbook:** `ingest/transitindex_ingest/workbook.py` (export-xlsx / import-xlsx
  round-trip). Restructure to reflect the linked + period model: period-aware sheets,
  derived columns that show the formula and the linkage, and the metric definitions
  inline so manual entry is unambiguous.

## Where to look
`lane-0-foundation-spec.md`, `data-model.md`, `schema-design.md`, `source-registry.md`,
`update-frequency.md`, and `balance-sheet-and-frequency-plan.md` (it already adds a
quarterly period + balance-sheet metrics — fold this restructure together with it). Plus
`ingest/transitindex_ingest/` (refdata, contract, jobs/derived_recompute, validation)
and `db/`. Check the relevant `TODOS.md` items (derived recompute, period comparability).

## How to work
Big and cross-cutting (schema + ingest + workbook + extraction). **Start in plan mode** —
explore the current model, then propose the restructure as a **phased plan** with the
migration path, and surface tradeoffs (especially: how back-solved values stay
"dispute-proof," how the equation graph resolves conflicts/over-determination, and the
period-rollup completeness rules). Don't write code until the plan is agreed. You **may
use a workflow / multi-agent orchestration** if it helps (e.g. parallel agents to spec
the metric dictionary or compare schema designs). Respect the invariants in `CLAUDE.md`
and `web/CLAUDE.md`.

## Heads-up
- The `design/web-review` branch (web cards + design fixes) is **unmerged**. Decide
  whether to merge/stash it first so this backend work starts from a clean base.
- The hardest design question is #1's "dispute-proof" tension: back-solving `expenses`
  from `farebox + revenue` is exact math, but the product promise is "nothing estimated,
  everything cited." Nail how a *derived* value records provenance and stays defensible.
