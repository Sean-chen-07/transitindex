# TransitIndex — Phased Plan & Tech Stack
**Version:** 0.4 | **Status:** Phase 1 proposal (no code until approved)

> **v0.4 (2026-05-29 CEO + Eng review):** sequencing and scope reconciled to the approved
> office-hours design, then expanded during eng review. The build is now **full Approach B**
> (real pipeline including the LLM PDF extractor + human review queue), sequenced into two
> milestones so revenue and the payment signal come first and the risky/novel piece is
> isolated off the critical path. The original "full UI on seed data first" order is dropped.
> See the CEO plan, the eng-review test plan, and TODOS.md.

---

## Tech stack (proposed)

| Layer | Choice | Why |
|---|---|---|
| Frontend | **Next.js 15 + TypeScript + React Server Components** | Server components suit data-dense pages; SEO matters for a discoverable directory; one ecosystem for SSR + API routes. Also load-bearing for paywall integrity (raw values stay server-side). |
| Styling | **Tailwind + shadcn/ui** | Fast spec-sheet aesthetic, consistent components. |
| Charts | **Recharts** (Visx if custom needed) | Covers trend/bar/compare charts cheaply; avoid Highcharts (licensing). |
| Database | **PostgreSQL 16** | Transit is small data; no TimescaleDB needed yet. JSONB escape hatch. |
| ORM | **Drizzle** (proposed) | Lean, SQL-honest. *Open — could flip to Prisma.* See schema-ownership note below. |
| Auth | **Auth.js (NextAuth)** — magic link + Google | Standard; defers password handling. Paid-path slice lands in Milestone 1 (see Identity). |
| Payments | **Stripe** | Metered $20/year subscription, linked to a paid account. |
| Hosting | **Vercel** (web) + **Neon/Supabase** (DB) | Cheap to start, scales linearly. *Open.* |
| **Ingestion** | **Separate Python repo** — FastAPI (review UI APIs), Prefect or cron (orchestration), pdfplumber + camelot (PDFs), Anthropic API (LLM-assisted extraction) | Strict separation: ingestion writes Postgres, web app only reads. No PDF parsing in Node. |

**Decoupling rule:** the web app never knows how data got into Postgres. Ingestion can be rebuilt without touching the user-facing app.

**Schema ownership (C1, user decision):** the database blueprint lives as **plain SQL
migration files** in a shared location — the single source of truth, owned by neither
service. A standalone migrate step applies them. This keeps schema evolution tool-agnostic
so future per-country pipelines (NTD, etc.) in any language conform to the same contract
without being locked to one ORM's migration tooling.
- **Guardrail:** the Next.js web app connects **read-only** and **introspects** the live
  schema to generate its read types (Drizzle introspect / `prisma db pull`) — it never
  defines tables. This enforces "web is a pure reader" even though no service "owns" the
  files (the discipline cost of neither-owns-it).
- The value contract (the canonical row shape every adapter emits) is what keeps new
  pipelines country-agnostic; the SQL files just define where those rows land.

Intended repo structure: `transitindex/web/` + `transitindex/ingest/`.

---

## Phases

### Phase 1 — Architecture & data model *(current)*
Written proposal: schema (data-model.md), stack (this file), ingestion strategy + source mapping (source-registry.md, update-frequency.md), launch agency list. **No app code until approved.**

### Phase 2 — Full Approach B build, sequenced in two milestones
**Scope expanded during the 2026-05-29 eng review (D2/D3):** the user chose to build the
full pipeline including the LLM PDF extractor + human review queue, not just the structured
slice. This is NO LONGER a ~1-week build. It is sequenced so revenue + the payment signal
come first and the risky/novel piece is isolated off the critical path. The office-hours
kill-line (>=3 of 10 buyers pay) becomes a post-Milestone-1 checkpoint, not a pre-build gate.

**Milestone 1 (revenue-capable, ships and earns first):**
- **Structured adapters, real data, auto-ingested:** StatCan 23-10-0307 (ridership +
  revenue, 7 of 10 agencies — TTC, STM, TransLink, Calgary, Edmonton, Metrolinx@GTHA,
  BC Transit@Victoria), Edmonton open-data (service hours), Calgary open-data (fleet),
  TransLink + Metrolinx quarterly where structured. No seed data.
- **Free, SEO-indexable directory shell:** every Canadian agency listed (name, province,
  modes); "fundamentals pending" on the long tail.
- **Sourced fundamentals pages:** headline + universal metrics, trend charts, latest
  period, mode badges, **per-metric "as of" dates**.
- **Free/paid value split (user decision):**
  - FREE tier shows the **rank** for each metric ("Ranked 3rd of 10") + the metric's
    "as of" date + the **attribution notice** — but NOT the raw number and NOT a clickable
    source deep-link.
  - PAID tier shows **everything**: the rank PLUS the raw sourced number PLUS full
    clickable page-level provenance/deep-links (the dispute-proof version).
  - **Rank, not percentile:** display ordinal rank 1..N. Direction from
    `metrics.higher_is_better` (lowest-wins for cost-per-rider, highest-wins for
    ridership; null = neutral, no good/bad framing).
  - **Rank against ALL agencies by default** (the "compared to Nvidia" model) — this is
    the FREE default. **Filtering is PAID:** paid users re-rank within **geographic scope
    (province / `subdivision`)**. (Typology dropped 2026-05-30 — typology re-rank removed; province
    is the paid re-rank dimension. A mode-based set can be added later if wanted.)
  - **Denominator correctness (mandatory):** rank MUST respect geographic/`comparable_flag`
    scope. StatCan's **Metrolinx** row is the **GO Transit + UP Express network** (what
    Metrolinx operates — NOT all GTHA systems, NOT GO-rail-only), so it maps cleanly to the
    Metrolinx/GO agency. The real scope caveat is **BC Transit = Victoria system only** (not
    the ~60-system whole). Flag/scope so a sub-system figure is never silently ranked as the
    whole agency.
  - **Paywall integrity (A1):** rank computed server-side; FREE API/RSC responses carry
    ONLY rank + "as of" + attribution — never the raw value or full-resolution chart
    points. The raw number must never ship in a free payload.
- **Identity (A3, user decision):** FREE browsing requires **no login** (anonymous, cookie
  soft-meter only — non-negotiable invariant). **Paying requires an account** (signup page
  or Google/OAuth via Auth.js), with the Stripe subscription linked to that account. The
  account is the paid identity, so cross-device re-entry just works. Thin paid-path-only
  slice of "accounts" lands here; full watchlist/dashboard accounts stay deferred to Phase 3.
- **Metered $20/year Stripe gate:** ~2 free fundamentals views/month then gated, via a
  **cookie/localStorage soft meter** (SEO-safe: Googlebot always sees free pages). Free
  directory stays indexable.
- **[accepted] Gate conversion instrumentation:** log wall-hit → gate-view →
  checkout-start → paid, tied to the triggering agency page.
- **[accepted] "Request this agency" demand logging:** action on pending directory pages
  that logs agency + timestamp (+ optional email). Pulls long-tail depth.
- **[accepted] Source-feed freshness/health alert:** each adapter records last-good fetch +
  row count + schema shape; cron alerts when a feed stalls past cadence or reshapes. On
  schema break, serve last-good data — never bad/stale-as-fresh data.

**Milestone 2 (the PDF pipeline, behind M1 — the one innovation token):**
- **LLM PDF extractor:** annual-report fundamentals (operating expenses, farebox recovery,
  fleet, service hours) for all 10 agencies; OC Transpo HTML ridership scraper.
- **Validation + flagging at staging:** yoy spike >50%, cross-source disagreement, unit
  mismatch, sum-doesn't-reconcile.
- **`pending_values` staging + human review queue UI (FastAPI):** every extracted value
  lands in `pending_values`; a human approves before it is promoted to `metric_values`.
  Invariant #1: an unreviewed value NEVER reaches live data.
- **Gold-fixture eval (T1):** ~10-20 hand-verified true values per agency; the eval asserts
  the extractor matches within tolerance AND flags its own uncertain values. Tracks
  precision on auto-approved values + flag-recall on misses. Doubles as the prompt/model
  regression guard.

### Phase 3 — Depth & accounts *(gated on the payment signal)*
- **Compare view:** select 2–4 agencies, spec-sheet layout, type-mismatch warnings (by modes + size, not typology).
- **Accounts (Auth.js):** full watchlist (star agencies → dashboard), persisted per user.

### Phase 4 — Long tail & expansion
Long-tail Canadian agencies (demand-pulled via "request this agency"); eventually US/NTD
as a new set of adapters emitting the same value contract, zero schema change.

---

## Ingestion strategy

**Premise:** PDFs are adversarial and inconsistent. Even good LLM extraction is ~5–15% wrong on edge values. **Every extracted number is wrong until a human confirms it.** Goal: a human reviews ~20 values per agency per year, not 200.

### Pipeline flow
```
discover (source registry) → download (cache, hash, dedupe) →
  parse (structured | LLM-assisted | manual) → stage in pending_values →
    review queue (web UI) → promote to metric_values + sources
```

### Validation flags at staging
- Year-over-year change > 50% → flag
- Cross-source disagreement (StatCan vs annual report) → flag
- Unit mismatch (e.g. missed "millions") → flag
- Sums don't reconcile (mode-level ≠ total) → flag

### Source tiers (detail in source-registry.md)
- **Tier 0 — auto-ingestible:** StatCan 23-10-0307 (monthly, by agency), municipal open-data CSVs, GTFS. No human review.
- **Tier 1 — structured per-agency:** city open-data portals (Calgary, Edmonton ridership/service hours).
- **Tier 2 — hard PDFs:** annual reports, budgets, board decks → LLM-assisted + human review queue.
- **Restricted:** CUTA (paid, anti-derivation terms) — back-room cross-check ONLY, never a cited public source.

### Build order (effort-to-coverage)
*(Items 1–2 are Milestone 1. Items 3–7 are Milestone 2, the PDF pipeline.)*
1. **StatCan 23-10-0307 adapter** — ridership + revenue for 7 agencies, one cron job.
2. **Edmonton + Calgary open-data adapters** — adds monthly service hours/fleet.
3. **TTC CEO Report PDF adapter** — sets the PDF pipeline pattern; builds the review queue.
4. **Annual-report PDF adapters** — operating expenses, fleet, farebox for all (the slow annual layer).
5. **OC Transpo** — monthly ridership is HTML/PDF only (needs scraper) + quarterly budget reports.
6. **MiWay / Burlington / BC Transit** — annual-only; do last.
7. **Metrolinx** — validates non-calendar fiscal year + regional-rail metrics.

---

## Launch agencies (10)

Chosen to exercise every agency type (modes, size, fiscal year, sourcing tier) and surface schema
gaps early. *(Typology was dropped as a stored field 2026-05-30; the "Typology" column below is
descriptive selection rationale, not a DB column.)*

| # | Agency | Typology | Why | Fiscal Year |
|---|---|---|---|---|
| 1 | **TTC** | Major Multimodal | Largest; bus+subway+streetcar+Wheel-Trans | Calendar |
| 2 | **STM** | Major Multimodal | Bus+métro; French reports test the parser | Calendar |
| 3 | **TransLink** | Major Multimodal | Bus+SkyTrain+SeaBus+commuter rail; best quarterly data | Calendar |
| 4 | **Metrolinx / GO** | Regional Rail | Commuter rail; non-calendar FY. **StatCan row = GO Transit + UP Express network** | **Apr–Mar** |
| 5 | **OC Transpo** | Mid-size Bus + LRT | "Mid-size that added rail" edge case. **Not in StatCan — HTML scrape** | Calendar |
| 6 | **Calgary Transit** | Mid-size Bus + LRT | Long-running CTrain; good open data | Calendar |
| 7 | **Edmonton ETS** | Mid-size Bus + LRT | Best-instrumented mid-size (monthly open data) | Calendar |
| 8 | **MiWay** | Mid-size Bus | Pure suburban bus; annual-only data. **Not in StatCan** | Calendar |
| 9 | **BC Transit** | Hybrid | ~60 community systems under one umbrella; parent/sub test. **StatCan = Victoria only** | **Apr–Mar** |
| 10 | **Burlington Transit** | Small Local Bus | The long tail; annual-only. **Not in StatCan** | Calendar |

The bet: if the schema + UI work for all ten, they work for the ~100+ remaining Canadian agencies.

---

## Data-sourcing reality (one-paragraph summary)

A fully legitimate, commercially-licensed product is buildable **without CUTA**: StatCan 23-10-0307 gives monthly ridership + revenue for the big agencies (commercially licensed, attribution required); agency annual reports/budgets (cited as primary sources) fill in expenses, farebox, fleet; municipal open data + GTFS add granularity. In Canadian law, individual facts aren't copyrightable and there's no EU-style database right — risk attaches only to copying someone's *original compilation/arrangement* (which is the CUTA trap). So: independently compile free-floating facts into our own structure, cite each one, keep CUTA in the back room. (Full detail in source-registry.md.)

**Provenance display (eng-review TENSION 1 resolution):** attribution is mandatory on BOTH
tiers for license compliance (invariant #8). FREE shows the attribution notice only (no
number, no deep-link); PAID gets the raw number + full clickable page-level provenance.
The required attribution text by source is listed in source-registry.md.

---

## Failure Modes Registry (eng review)

| Codepath | Failure mode | Test? | Error handling? | User sees? |
|---|---|---|---|---|
| StatCan adapter | Unmapped agency code | T5 (IRON) | skip + ALERT | nothing silent — alert fires |
| Free API/RSC | Raw value leaks into free payload | T1 | server-side strip | paywall holds |
| PDF promote | Unreviewed value reaches `metric_values` | T6 (IRON) | `pending_values` is only door | reviewed data only |
| LLM extractor | Malformed/refusal response | T8 eval | flag for review, never write | value held for review |
| Rank compute | Mismatched geographic scope (BC Transit = Victoria only vs whole-agency figures) | T2 | scope/comparable_flag guard | no misleading rank |
| Source feed | Feed stalls / reshapes | T9 | serve last-good + alert | "as of" stays honest |

No row is RESCUED=N + TEST=N + SILENT. **No critical gaps.**

## Worktree Parallelization

Two deployable units with a clean contract (the SQL schema) between them → genuine parallel lanes.

| Step | Modules | Depends on |
|---|---|---|
| Schema migrations | `migrations/` | — (do first) |
| Structured adapters | `ingest/` | schema |
| Web (directory, fundamentals, rank, gate, auth) | `web/` | schema |
| PDF pipeline + review queue (M2) | `ingest/`, review UI | schema, adapters |

- **Lane 0 (blocking):** schema migrations — both lanes need the contract first.
- **Lane A:** `ingest/` structured adapters → PDF pipeline (sequential, shared module).
- **Lane B:** `web/` (independent of ingest once schema exists; reads via introspection).
- **Execution:** ship Lane 0, then run A + B in parallel worktrees. M2 (PDF) is a later A-lane step.
- **Conflict flag:** both lanes touch `migrations/` only at the start — coordinate the initial schema, then they diverge cleanly.

---

## Design — UI/UX spec (plan-design-review, 2026-05-30)

Established via `/plan-design-review` against 5 hand-built HTML wireframes (no OpenAI
key, so AI mockups were skipped in favour of precise wireframes). Visual system extracted
to **DESIGN.md**. Initial design completeness **3/10 → 9/10**. 12 decisions made (D3–D12).

### Product/UX model (the spine)
- **FREE** — an expandable directory of every Canadian agency (search hero + province
  groups). A card per agency shows ranks as plain ordinals ("1st"). Click → the card
  **expands in place** (dropdown) to all ranks + the trend shape; scroll past to the next
  agency, no back button. Always free, always crawlable (the SEO surface).
- **PAID** — `Open full data` → a full-depth **spreadsheet** (financial-statement tabs:
  Ridership & Service / Financials / Fleet & Assets / Trends) with real numbers, rank,
  period, as-of, YoY, and a sparkline per metric.
- **GATE** — **1 free detail view per visitor per month** (cookie soft-meter), then the
  paywall. The server renders detail pages (Googlebot + first-click-from-search see them →
  indexable); the meter walls the 2nd+ human view. $20/yr Stripe. *(Revised from a pure
  hard gate to recover SEO + give a taste before the wall.)*

### Decisions (D3–D12)
| # | Decision | Choice |
|---|---|---|
| D3 | Aesthetic | Mini-Motorway-soft free surface; dense spreadsheet paid surface; Outfit type (see DESIGN.md) |
| D4 | Rank display | Plain ordinals ("3rd"); comparison set stated **once per page**, not "(3 of 10)" on every number |
| D5 | Gate | **Superseded by eng re-review** → account-gated numbers (server-side); web = free public ranks (SEO, no login, no tracking); no anonymous metering. See "Architecture — eng re-review" below |
| D6 | Provenance | Source **links dropped entirely** (even paid); precise text citations kept in a tiny bottom footnote — satisfies invariant #1 in words |
| D7 | Information architecture | **Both** — search hero + province-grouped expandable list (free directory is the only SEO surface) |
| D8 | Partial data | Show an agency card as soon as **any** metric is sourced; missing → "not yet sourced" (max indexable coverage) |
| D9 | Detail-page ranking | Rank vs **all** by default (matches the free card); switch to region (province) on the paid page (typology dropped 2026-05-30) |
| D10 | Mobile | Bloomberg / Yahoo-iOS **3-level**: list → full card → tabbed sheet |
| D11 | Directory interaction | **Expand in place** (accordion), not a page jump |
| D12 | Ratios | **Strict period-match** (annual); no mixed-period / TTM estimates; ratios live in the Financials tab labeled "as of FYxxxx" |

### Interaction states (what the user sees)
| State | Where | What the user sees |
|---|---|---|
| Loading | detail sheet | skeleton rows (greyed bars), tabs stay — not a spinner |
| Pending (no data) | directory card | dashed card, "Fundamentals pending", "+ Request this agency" |
| Partial data | card / sheet | available ranks shown; missing → "— not yet sourced" (D8: card shows on any metric) |
| Stale feed | metric row | honest "as of"; if past expected cadence, date muted + amber "may be outdated" (ties to feed-health alert) |
| 0 results | directory | "No agency matches 'X'. Browse by province ↓" + the grouped list |
| Scope caveat | card + sheet header | BC Transit "Victoria system only", Metrolinx "GO + UP Express" inline — a sub-system figure is never read as the whole agency |
| Restated value | metric row (paid) | current value + small "restated" tag (invariant #5) |

### Data display rules
Per-metric Period + As-of (never one agency-level stamp); derived metrics inherit the
slowest input's period **and** same-period values; ratios strictly period-matched (D12);
ranks compare same period + scope, and carry their period. Full rules in DESIGN.md.

### Build rule for eng / data-model (flag from this review)
**Ranks must compare the same period across agencies, not only the same scope.** Add
period-comparability to rank computation: an agency missing the latest period ranks on its
latest comparable period or sits out that period's rank (flagged), never silently mixed.
→ record in data-model.md and confirm in eng review.

### Responsive & accessibility
WCAG 2.1 AA baseline committed (real table semantics, screen-reader rank labels, mode group
by icon+label not color alone, focus-trapped gate dialog, 44px touch targets, body ≥16px,
contrast ≥4.5:1, sparkline text alternatives). Responsive model per DESIGN.md.

### Approved mockups (visual reference)
| Screen | File (`~/.gstack/projects/transitindex/designs/core-screens-20260529/`) | Notes |
|---|---|---|
| Desktop free→paid + gate | `wireframes-v3.html` | cards → spreadsheet → paywall; tiny text-only sources |
| Mobile L1→L2→L3 | `wireframes-v4-mobile.html` | list → full card → tabbed data sheet |
| Expand-in-place directory | `wireframes-v5-expand.html` | current home interaction (accordion) |

### NOT in scope (deferred, with rationale)
- **AI-generated mockups / aesthetic variants** — no OpenAI key; revisit via `design setup` if you want style exploration.
- **Clickable source deep-links** — dropped (D6); revisit only if buyers say the live "prove it" click is why they'd pay.
- **Fresher TTM ratio estimates** — rejected (D12) as attackable; revisit only on buyer demand.
- **Compare view, accounts/watchlist** — already Phase 3.

---

## Architecture — eng re-review (plan-eng-review, 2026-05-30)

Focused re-review of the three changes the design review introduced. The schema
(data-model.md) already supports them structurally; these pin the missing behavior.

### Paywall + tracking (supersedes design D5 metering)
- **Numbers are account-gated server-side.** Raw values NEVER ship to an unauthenticated
  client (restores prior invariant A1). The design review's "1 free detail view/month"
  cookie meter is **dropped** — a client-side meter + crawlable full-detail made the paid
  dataset trivially scrapeable.
- **Web = free public ranks** (cards + ranks), fully crawlable, no login, no tracking — the
  SEO/acquisition funnel. Detail pages render ranks (not numbers) to anonymous/crawlers, so
  they stay indexable; the numbers gate behind a paid account.
- **No anonymous metering** → nothing tracks free users. (Metering an anonymous user is the
  only thing that needed a device identifier; dropping it removes the App Store ATT concern.)
- **Native app deferred to Phase 3** (D3): the responsive web app is the MVP's mobile
  experience. If built later, Capacitor-wrap the web UI, login-gated paid-only (reader-app
  pattern, purchase on web) → avoids Apple's IAP cut. Free taste = the rank directory; a
  demo-agency full preview can be layered later if conversion is weak.

### Rank computation (D4) — materialized, backend
- A **`metric_ranks`** table is materialized in the data layer and refreshed when values are
  promoted/restated (read-heavy on the SEO surface, write-rare). Ranks are not computed at
  request time.
- **Period-comparability rule:** rank within the latest period bucket where enough agencies
  have comparable values (`comparable_flag` + matching `service_scope`). An agency missing
  that period shows **"not ranked — latest FYxxxx"**, never ranked against a different year.
  Same rule guards scope (BC Transit = Victoria, Metrolinx = GO+UP). Implemented once in the
  refresh job.

### Derived ratios (D5) — post-promotion recompute, stored
- A **derived-recompute step** (same backend layer as the rank job) computes period-matched
  ratios (cost-per-rider, farebox recovery, subsidy-per-rider) from current approved inputs,
  stores them as first-class `metric_values` at the shared annual period, runs automatically
  (math on already-reviewed numbers), and re-runs on input promote/restate (no stale ratio).
  Keep an automated sanity flag (farebox >100%, negative cost).
- **Opt-in "Estimate" mode (user toggle):** off by default. When ON, ratios are recomputed
  **on-demand from the latest available inputs** (periods may differ) and shown clearly marked
  as an estimate. Estimate ratios are **never stored**, **never ranked**, and show **no trend
  graph** (a single synthetic point — the absent trend is the visual signal that it's a guess).
  The strict period-matched value remains the default and the only dispute-proof number.
- Both jobs should be **incremental** (recompute only the affected metric/period/agency
  cohort on a value change), not full rebuilds.

### New test requirements (CRITICAL/IRON in bold)
- **Rank period-comparability** — same-period-only; missing-period agency → "not ranked".
- **Paywall integrity** — unauthenticated detail request returns ranks only, never raw numbers.
- **Derived restatement recompute** — correcting an input re-runs the ratio, no stale value.
- Rank scope guard (BCT/Metrolinx); derived period-match; derived sanity flag.

### Documented risks (outside voice 2026-05-30 — surfaced; user chose to proceed with full Approach B)
Recorded, not acted on (user re-affirmed the full build). Revisit if the demand signal is weak.
1. **SEO funnel is unproven (highest).** Crawlable pages are ranks-only (no numbers, no source
   links) — risk of thin-content demotion AND no conversion taste. Cheap hedge: publish a few
   agency pages early, watch Search Console indexation/impressions before relying on SEO for traffic.
2. **Over-build for a 10-buyer test.** The full pipeline ships before the payment signal (kill-line
   deferred past M1). The plan's own "don't scale the cost center on conviction" still applies to M2.
3. **M1 rank denominators may be small.** Most launch agencies' annual numbers live behind the M2
   PDF pipeline, so M1 ranks lean on the 7 StatCan ridership/revenue agencies — marquee ranks could
   read "1st of 2" / "not ranked". **Define a minimum denominator** (e.g. suppress rank below N≥5).
4. **$20 self-serve may mis-measure civic demand** — probe price + approval level with the 10 buyers,
   not just a binary at $20.
5. **Launch-10 maximize heterogeneity** — great for schema-stress, weak for a clean-comparability
   demo; consider leading the demo with the 3 big multimodal agencies on clean StatCan data.

---

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 1 | done | SELECTIVE EXPANSION; 4 cherry-picks accepted; sequencing reconciled |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 2 | clean | round 1: 7 issues (A1-A3, C1, T1, 2 tensions). round 2 (re-review of design changes): 3 arch findings resolved — paywall account-gate (closes A1 hole the metering reopened), materialized `metric_ranks` + period rule, derived-recompute step; 3 IRON tests added; 0 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 1 | done | 3/10 → 9/10; 12 decisions (D3–D12); 5 wireframes approved; DESIGN.md created |

- **OUTSIDE VOICE:** Claude subagent (codex unavailable). Surfaced 3 whole-plan catches:
  free/paid line, rank-against-all default, and a real denominator-scope bug. All 3 put to
  the user; 2 cross-model tensions resolved interactively, 1 (provenance display) corrected
  to keep license compliance.
- **CROSS-MODEL:** the eng section pass and the outside voice agreed the schema is sound and
  the decoupling is justified; they diverged on free/paid economics and rank default — both
  resolved by user decision.
- **UNRESOLVED:** 0. All decisions answered (D1-D3, A1-A3, C1, T1, TENSION 1-2).
- **NOTE (env):** not a git repo + `jq` missing → review-dashboard reads NO_REVIEWS and the
  autoplan task-JSONL was skipped. Decisions are captured in this plan, the CEO plan, and
  the eng-review test plan instead.
- **DESIGN:** plan-design-review complete (3/10 → 9/10). Free directory (expandable cards,
  ordinal ranks) → paid spreadsheet (financial-statement tabs); 1-free-detail/month gate;
  Mini-Motorway-soft free surface + Bloomberg-dense paid surface; sources text-only at the
  bottom; strict period-matched ratios; WCAG 2.1 AA baseline. Full spec in the Design
  section above + DESIGN.md. New eng flag raised: rank period-comparability (not just scope).
- **ENG RE-REVIEW (2026-05-30):** validated the 3 design-introduced changes. Key correction:
  the design review's 1-free-detail cookie metering reopened the paywall scrape hole (invariant
  A1) — resolved to **account-gated numbers + free public ranks + no anonymous tracking**, native
  app deferred (web-first MVP). Rank model + derived-ratio computation pinned to the backend
  (materialized `metric_ranks`, post-promotion derived recompute). See "Architecture — eng
  re-review" above.
- **OUTSIDE VOICE (eng, Claude subagent — codex unavailable):** challenged scope + the SEO funnel
  as over-built/unproven for a 10-buyer test. User chose to proceed with full Approach B (D7=B).
  5 risks recorded above (not acted on); highest is the unproven ranks-only SEO funnel.
- **VERDICT:** CEO + ENG (x2) + DESIGN reviewed; scope + UX + architecture locked, 0 critical
  gaps. Ready to implement Milestone 1 once you approve. New schema artifacts to add at build:
  `metric_ranks` table + the rank-refresh and derived-recompute jobs (see data-model.md).

---

## RE-REVIEW (2026-05-31, /autoplan, codex unavailable → subagent + direct code reads)

Re-ran the full pipeline against **merged Lane 0 + Lane A code**. The original review
graded the plan as a *plan* (no code existed). This pass graded it against reality and
found the "0 critical gaps" status is **overstated** — the plan and the merged code have
drifted. Findings below were verified by reading the cited files.

### Headline: the build inverted its own sequencing
The plan's defense of "full Approach B" is "revenue comes first, the risky piece is off the
critical path." Reality: **M2 (PDF/vision pipeline — the deferrable cost center) is fully
built and merged; M1 (web app — the revenue + payment-signal engine) is 0% started**
(`web/` = a single `.gitkeep`). The kill-line (">=3 of 10 buyers pay") now sits behind an
unbuilt M1 → the innovation token was spent before the test that authorizes it.

### Verified findings (file:line)
- **ENG-5 (CRITICAL data bug):** `statcan_307.py:40` stores *monthly* StatCan trips under
  `metric_code="annual_ridership"` (docstring `:3`/`:15` says monthly; `:95` writes
  `period_type="monthly"`). Marquee "annual ridership" rank = one month; `cost_per_rider`
  goes ~12× wrong once PDF annual expenses land. `test_statcan_307` asserts the bug.
- **ENG-2 (HIGH):** "paywall holds / 0 critical gaps" is false — `web/` is empty; A1 paywall
  has zero code + zero tests; `web_reader` grant = SELECT on raw `metric_values`.
- **ENG-11 (HIGH security):** `review/app.py:91` `POST /approve` (only door into
  `metric_values`) has no auth. Localhost default mitigates; a public bind defeats Invariant #1.
- **ENG-4 (HIGH drift):** `refresh_ranks` has no period-comparability logic — missing-period
  agency silently vanishes; no "not ranked — latest FYxxxx" row. Plan claim unimplemented.
- **ENG-6 (HIGH contradiction):** schema DECISION 3 dropped the scope-caveat guard, but the
  plan invariant + Failure Modes T2 still claim it. Code follows schema (no guard) → BC Transit
  (Victoria-only) ranked vs TTC whole-system, no caveat.
- **ENG-10 (HIGH):** live ingest runs with validation disabled (`prior_value=None`;
  PDF `validator=None`) → YoY/sum/cross-source flags are dead in real runs; "20 not 200"
  reviews/agency promise is unbacked. No Postgres-backed CI test (in-memory repo only).
- **DESIGN (CRITICAL contradiction):** `DESIGN.md:65` + all 3 approved wireframes still spec
  the KILLED "1 free / used" cookie-meter paywall (superseded by D5/account-gate, plan
  lines 308-322). An implementer following DESIGN.md rebuilds the scrapeable paywall. No
  "numbers gated (anonymous)" state in the interaction-states table.
- **DESIGN/CEO (cross-phase, the plan's own #1 risk):** the free SEO surface is ranks-only,
  no numbers, no source links (D6) → thin-content risk AND no conversion taste. Re-flagged
  by both voices independently.
- **CEO premises (all unvalidated):** SEO-funnel-works, $20-self-serve-fits-civic-buyer,
  PDF-5-15%-wrong. Gold fixture `ttc_annual_2024.json` reads as synthetic.

### Premise gate outcome (2026-05-31)
User declined all three cheap validation tests; raised **FOI/ATIP requests** as an
alternative data-sourcing route. Assessment: FOI is the wrong *primary* channel (not a
feed, fees + commercial scrutiny, most fundamentals already published → redirects to the
PDF), but a narrow *informal data request* to each agency is high-leverage to (a) skip
extraction where agencies share the Excel and (b) get **real ground-truth to replace the
synthetic gold fixture**. FOI planning spun out to subagents (see separate FOI plan).

### Re-review consensus (single-voice, codex unavailable)
- CEO: 6 dimensions flagged; 1 User Challenge (sequencing inverted in code).
- Design: 9/10 → **6/10** (drift) — killed-paywall contradiction + missing error/gated/N<5
  states + unanswered trust gap.
- Eng: value-contract door HOLDS + decoupling sound + eval real; but 1 verified data bug,
  1 security gap, paywall unbuilt, period-comparability + scope-guard + live-validation gaps.

<!-- AUTONOMOUS DECISION LOG -->
### Decision Audit Trail (re-review)

| # | Phase | Decision | Classification | Principle | Rationale |
|---|-------|----------|----------------|-----------|-----------|
| 1 | CEO | Surface 3 unvalidated premises to user | GATE (not auto) | — | Premises need human judgment; user chose to validate none |
| 2 | CEO | Sequencing inverted (M2 built, M1 empty) → final gate | USER CHALLENGE | — | Both available voices say direction should change; user owns it |
| 3 | CEO | Concierge "sell the spreadsheet" MVP | Defer to TODOS | P3/P6 | Cheapest demand test; flag not block |
| 4 | Eng | Fix `statcan_307` monthly-as-annual mislabel | Mechanical (FIX) | P1 | Verified correctness bug in merged code |
| 5 | Eng | Add auth to review `/approve` before non-localhost | Mechanical (FIX) | P1 | Verified security gap; only door to live data |
| 6 | Eng | Correct "paywall holds / 0 gaps" → UNVERIFIED | Mechanical | P5 | Factual: web/ is empty |
| 7 | Eng | Wire live validation (`prior_value`, cohort, PDF validator) | Mechanical (FIX) | P1 | Flags dead in real path; blast-radius, <1d |
| 8 | Eng | Add Postgres-backed CI test (apply migrations + db/tests) | Auto (ADD) | P1/P2 | In-memory repo reimplements invariants; real SQL untested |
| 9 | Eng | Period-comparability: BUILD vs downgrade plan claim | TASTE → gate | P1/P5 | Reasonable disagreement on scope-now vs defer |
| 10 | Eng | Scope-guard contradiction: re-add guard vs delete claim | TASTE → gate | P1 | Correctness vs DECISION-3 simplicity |
| 11 | Design | Reconcile DESIGN.md/wireframes to account-gate model | Mechanical (FIX) | P5/P1 | Doc contradicts a locked decision |
| 12 | Design | Add error + gated-anon + N<5 states to states table | Auto (ADD) | P1 | Load-bearing launch states missing |
| 13 | Design | SEO trust-builder (reverse D6: one free source link / demo agency) | TASTE → gate | P1 | Reverses a locked decision; user's call |
| 14 | Eng | Replace synthetic gold fixture w/ real agency values | Auto (ties to FOI) | P1 | Eval grades vs made-up answers today |
