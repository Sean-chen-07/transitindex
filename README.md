# TransitIndex

> **Project orientation.** This file explains what the project is and how it's structured. Detailed specs live in the sibling docs linked below.

## What this is

A **"Yahoo Finance for public transit."** Transit agencies publish performance and financial data in scattered PDFs that nobody reads. TransitIndex aggregates it into a clean, sourced, structured database and presents it on a public website where anyone can browse an agency's "fundamentals," view trends, and compare agencies side by side like products on a retail site.

- **Starting market:** Canada. Schema designed so the US (via NTD) and international agencies can be added later without re-architecting.
- **Business model:** **Everything is paid** — no free tier. Access is **metered** (~2 free agency views/month, then gated), not a hard wall, to keep the directory discoverable/SEO-visible. See decisions below.
- **Primary user:** **Civically-engaged non-experts** — politicians, city/regional officials, nonprofits & advocacy groups who must care about transit but aren't close enough to see the full picture. The product's core job is **translation**, not just aggregation.

## ⚠️ Current status: PHASE 1 — PLANNING. NO APPLICATION CODE YET.

**Do not write application code until the user explicitly approves the plan.** We are still finalizing the architecture, data model, and data-sourcing strategy. The work so far is research and design, captured in the docs below.

## Document index

| File | Contents |
|---|---|
| **README.md** (this file) | Orientation, invariants, decisions, open questions |
| **data-model.md** | The database schema — entities, columns, rationale |
| **phase-plan.md** | Phased roadmap, tech stack, ingestion strategy, launch agencies |
| **source-registry.md** | Every launch agency × metric × specific data source + license |
| **update-frequency.md** | Every agency × metric × finest available update frequency (monthly/quarterly/annual) |

## Non-negotiable invariants

These are the load-bearing principles. The entire value of the product is trustworthy, comparable, well-sourced data. Violating these breaks the product.

1. **Provenance is mandatory.** Every public number must trace to a source document + page (or dataset + retrieval date). No orphan numbers. Ever.
2. **Per-metric freshness.** Data updates at three speeds — ridership (monthly), some revenue/expenses (quarterly), fundamentals like farebox recovery (annual). The UI shows an "as of" date **per metric**, not one date per agency. See update-frequency.md.
3. **Derived metrics inherit their slowest input.** Farebox recovery = revenue/expenses; since expenses are annual for ~9 of 10 agencies, farebox recovery is annual. Never imply a derived metric is fresher than its inputs.
4. **`service_scope` on every value.** Conventional vs specialized (paratransit) vs total are distinct rows — never silently summed or double-counted.
5. **Restatements are versioned, not overwritten.** Agencies revise prior figures. Keep the chain; charts read the current value, an audit view shows history.
6. **Fiscal years vary.** Store period start/end dates, not just year labels. Metrolinx & BC Transit run Apr–Mar; most others are calendar. Compare view must handle and flag mismatches.
7. **CUTA is back-room only.** CUTA's stats product is paid and its terms forbid deriving a commercial product from it. Use it ONLY as a private cross-check — NEVER as a cited public source. Every public number comes from a primary source we're licensed to use (StatCan, agency reports, municipal open data).
8. **Attribution is required** on StatCan and municipal open-data sources. Render the required notice text (see source-registry.md). This is a feature — visible citations are the trust story.
9. **Frontend and ingestion are decoupled.** Ingestion (Python) writes to Postgres; the web app (Next.js) only reads. No PDF parsing in Node land.

## Decisions made

| Decision | Choice | Date |
|---|---|---|
| Business model | **Everything paid** — no free/Pro feature split. | 2026-05-29 |
| Paywall mechanics | **Metered gate** — ~2 free agency views/month, then locked. Chosen over a hard gate to keep the "discoverable directory" SEO story intact. Refines the earlier "single hard gate." | 2026-05-29 |
| Primary target user | **Civically-engaged non-experts** — politicians, city/regional officials, nonprofits & advocacy groups: care about transit but aren't close enough to see the full picture. Implication: core job is *translation*, not just aggregation. | 2026-05-29 |
| History at launch | **5 years** — spans pre-COVID baseline → COVID crash → recovery without exploding PDF-extraction volume. | 2026-05-29 |
| Data model layering | **One flat metric layer** — dropped the universal/mode-specific/typology *three-layer* concept as a user-facing structure (it was always one physical table anyway). | 2026-05-29 |
| Typology | **Dropped (2026-05-30).** Modes + `service_area_population` already carry agency scale (a subway operator is a big one), so a separate category tag was redundant. Paid re-rank now uses province (`subdivision`). See lane-0-foundation-spec.md. | 2026-05-30 |
| Update frequency | Pursue **monthly/quarterly where available**, not annual-only. Researched and confirmed feasible — see update-frequency.md. | 2026-05-29 |
| Project location | `C:\Users\chenc\projects\transitindex\` — dedicated folder, isolated from rest of system. | 2026-05-21 |
| Current focus | Data layer first; UI deferred. | 2026-05-29 |

## Recommended defaults (proposed, NOT yet confirmed by user)

Use these unless the user decides otherwise:
- **Stack:** Next.js 15 + TypeScript (web), PostgreSQL 16, Recharts, Python + FastAPI (ingestion). See phase-plan.md.
- **ORM:** Drizzle (lean, SQL-honest). *Open.*
- **DB host:** Neon or Supabase Postgres. *Open.*
- **Restatement display:** show latest + "restated" badge with drill-in. *Open.*
- **Compare-view fiscal alignment:** align by each agency's native fiscal year + warn on mismatch. *Open.*
- **Paratransit:** one agency page with `service_scope` filtering (not a separate agency). *Open.*
- **Provenance granularity:** page-number level at launch (bounding-box deep-links deferred — ~2× ingestion cost). *Open.*

## Open questions (unresolved)

- **Legibility vs. neutrality** *(new — raised by the target-user decision)*: for the non-expert audience, how far do we interpret metrics — peer percentiles + directional cues only, or a composite score/grade? Recommendation: factual framing, **no editorial grade** (protects invariant #1). Needs a decision.
- Is seed/demo synthetic data acceptable (clearly watermarked) for early UI?
- Whether to actually contact CUTA for licensing terms (user said skip for now)
- Confirm the "recommended defaults" above

## Working style

- **Plan before code.** Phase 1 is a written proposal for approval. Do not start coding until the user signs off.
- **Favor a clean, flexible schema over a quick one.** Trustworthy, comparable, sourced data is the whole product.
- **Accuracy and provenance are central.** When researching data sources or licensing, verify against primary sources — don't state legal/licensing facts from memory.
- **Keep all project files inside** `C:\Users\chenc\projects\transitindex\`. Do not touch files elsewhere on the user's system.
- Eventual repo structure: `web/` (Next.js) and `ingest/` (Python), decoupled.
