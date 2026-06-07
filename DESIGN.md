# TransitIndex — Design System (DESIGN.md)

> **Status:** v1, established by `/plan-design-review` on 2026-05-30 from approved
> wireframes (`~/.gstack/projects/transitindex/designs/core-screens-20260529/`).
> No app code exists yet — this is the visual + interaction contract the build follows.
> Calibrate every UI decision against this file.

## Design thesis — two moods, one product

- **FREE directory = approachable, calm, "Mini Motorway"-soft.** Warm cream canvas,
  rounded cards, soft shadows, friendly geometric type, generous space. Job: pull a
  civically-engaged non-expert in and show where their agency ranks.
- **PAID detail = dense, efficient spreadsheet (Bloomberg / Yahoo Finance).** Tight
  rows, gridlines, tabular numbers, financial-statement tabs. Job: show every number
  as effectively as possible to someone who paid for the data.

The transition from soft cards to dense sheet **is** the free→paid story. Don't make
the free side a terminal; don't make the paid side bubbly.

## Typography
- **Primary family:** Outfit (Google Fonts), weights 400/500/600/700/800. Geometric,
  friendly, modern. **Never** system-ui / Inter / Roboto / Arial as the primary face.
- **Numbers:** Outfit with `font-variant-numeric: tabular-nums` everywhere figures
  align (rank grids, the spreadsheet). Comparability is the product — numbers line up.
- One face for v1. Revisit a second/editorial face only if the free surface wants more character.

## Color tokens (warm, low-chroma; define as CSS variables)
```
--bg      #F4F0E7   warm cream canvas
--card    #FFFFFF   --card-2 #FBF9F4
--ink     #2E2C28   --ink-2 #5F5B52   --ink-3 #6E6960   (ink-2/3 darkened to clear WCAG AA on cream)
--line    #ECE6D9   --line-2 #F3EEE3   --grid #E7E1D4 (spreadsheet rules)
--coral   #E2725B   (+ soft #FBE9E3)  primary action · paywall/upsell · "Paid"
--teal    #3F9D92   (+ soft #E1F0ED)  interactive · "Free" · positive
```
**Mode-group accents — color-CODE only, never the sole signal (always paired with a label/icon):**
Accent derives from each agency's **modes** (typology was dropped 2026-05-30 — see
lane-0-foundation-spec.md), not a stored category. Provisional grouping reusing the palette:
`--teal` rapid-rail (has subway) · `--blue #7BA7C7` commuter-rail · `--sage #9DBF8E` light-rail ·
`--yellow #E9B850` bus-only · `--coral` mixed. **Exact mode→color mapping is a design-review
follow-up** (replaces the old 5-typology palette).

**Rank direction is NEUTRAL.** No green/red good-bad coloring — `metrics.higher_is_better`
can be null (e.g. cost-per-rider lower-is-better, ridership higher-is-better, some neutral).
A rank is just an ordinal. No editorial grade, ever (protects invariant #1).

No purple/violet gradients. No decorative blobs. No icon-in-colored-circle feature grids.

## Shape & space
- Radius: free cards 16–20px (soft); spreadsheet cells ~6px (tight); pills 9–20px.
- Shadows: soft and low (`0 6px 20px rgba(60,50,30,.06)`); elevate on hover / for the gate dialog.
- Generous padding on free surfaces; tight, gridlined rows on the paid sheet.

## Components
1. **Agency card (free):** mode-group color bar, name, city, mode pills, rank
   grid (ordinals "1st"), 1–2 peek metrics + chevron. **Expands in place** (accordion).
2. **Expand panel (free):** all ranks (each with its own "as of"), trend **shape**
   (exact values locked), `Open full data →` (paid). Scroll past to next agency, no back button.
3. **Spreadsheet (paid):** financial-statement tabs — *Ridership & Service / Financials /
   Fleet & Assets / **Financial Position** / Trends*. Columns: Metric · Value (tabular,
   right-aligned) · Rank · Period · As of · YoY · 5-yr sparkline. Zebra rows, hairline grid,
   hover tint. The **Financial Position** tab (added 2026-05-31) holds the balance sheet — a
   point-in-time *snapshot* at fiscal year-end, kept separate from the flow-based *Financials*
   tab so each tab's "as of" stays honest. Three plain-language sections: *What the agency owns*
   · *What it owes* · *Net position*. Raw dollars are paid-only and unranked; only
   `net_debt_per_capita` and `debt_to_assets` carry ranks. See
   [balance-sheet-and-frequency-plan.md §5](balance-sheet-and-frequency-plan.md).
4. **Rank display:** ordinal only ("3rd"); comparison set named **once per page**
   ("ranked vs all Canadian agencies"), not "(3 of 10)" on every number. Paid switches
   the set (region / province).
5. **Paywall dialog:** "1 free / used" meter, what-you-unlock list, one coral CTA,
   sign-in, reassurance. Focus-trapped, ESC closes, dimmed background `aria-hidden`.
6. **Source footnote:** tiny, **text-only, no links**. Names each source + license +
   retrieval date; "Ranks computed from these; nothing estimated." Bottom of the detail only.
7. **Badges/pills:** mode pills, mode-group tag (icon + label), "Free" / "Paid view" flags.
8. **States:** skeleton rows (loading), pending/request card, partial "— not yet sourced",
   stale "as of" muted + amber, 0-results, scope caveat inline.

## Data display rules (load-bearing for trust)
- **Per-metric `Period` + `As of`.** Never one agency-level "last updated" stamp.
- **Derived metrics inherit the slowest input** — its period AND its same-period values
  (not just the date). Show a "= a ÷ b" note.
- **Ratios are strictly period-matched** (annual) by default: cost-per-rider = FY2024
  expenses ÷ FY2024 ridership, labeled "as of FY2024".
- **Estimate toggle (opt-in):** off by default. When on, ratios recompute on-demand from
  latest inputs, shown with a clear "est." marker and **no trend graph** (the missing trend
  signals it's a guess, not history). Estimates are never stored or ranked.
- **Ranks compare same period + same scope** across agencies. Rank carries its period.
  Scope caveats shown inline (BC Transit = Victoria system; Metrolinx = GO + UP Express).
- **Carry-forward (display only).** When a metric's newest value is older than the current
  period (e.g. an annual balance sheet beside monthly ridership), the headline row carries the
  last known value forward, styled with the **amber stale-feed state** + a "carried forward"
  label. It is never ranked; **trend charts show a gap**, never a flat carried segment or
  interpolation (same signal as the estimate toggle's missing trend). Nothing is ever fabricated
  into the data — carry-forward is purely a reading affordance.

## Accessibility — WCAG 2.1 AA baseline
- Real `<table>` semantics (caption, `scope` on `th`) for the spreadsheet.
- Screen-reader rank labels: "ranked 1st of 10" even when the visual shows "1st".
- Mode group by **icon + label**, never color alone.
- Focus-trapped paywall dialog; ESC to close; visible focus rings.
- 44px min touch targets; body text ≥16px; contrast ≥4.5:1 on body text.
- Trend/sparkline has a text alternative (e.g. "+4.1% over 5 years").
- Preserve visited vs unvisited link distinction.

## Responsive
- **Desktop:** ONE unified expandable row list (search hero + a single table of every
  agency; province is a column/search term, **not** separate per-province grids — see the
  2026-05-31 layout note below) → paid spreadsheet.
- **Mobile (Bloomberg / Yahoo-Finance-iOS):** L1 list (name + 1–2 ranks) → L2 full card
  (all ranks, free) → L3 tabbed data sheet (paid). Sheet rows tap-to-expand for
  period / as-of / sparkline.

## Approved wireframes (visual reference of record)
`~/.gstack/projects/transitindex/designs/core-screens-20260529/`
- **wireframes-v3.html** — desktop: free cards → paid spreadsheet → gate
- **wireframes-v4-mobile.html** — mobile L1 → L2 → L3
- **wireframes-v5-expand.html** — expand-in-place directory (current home interaction)

Superseded: v1 (terminal/IBM-Plex look) and v2 (inline per-number source chips) — rejected.

## Status update 2026-05-31 — directory layout: one unified table, not province grids

The home directory is now **one continuous, table-like list of every Canadian agency**, not
the per-province card grids this file originally specced (Components #1 + the old Responsive
line). Decision drivers: (a) the directory scaled from 10 launch agencies to the full
~100+-agency census (`db/seeds/06_agencies_full.sql`), where separate per-province grids
fragment the page; (b) the user asked for "all together in a table format." Each agency is a
**full-width row** (mode-group color bar → name link → province column → 1–2 peek ranks →
expand chevron) that **expands in place** to all ranks (the wireframes-v5 interaction,
unchanged). Province is a **column + search term**, not a grouping. The interaction, tokens,
expand-in-place behaviour, rank-only free payload, and N<5 suppression are all preserved —
only the page-level arrangement (grids → single table) changed. wireframes-v5-expand.html
remains the row/expand reference of record; the v3/v5 multi-column or province-grouped
arrangements are superseded for the home by this single-table layout.

## Status update 2026-06-06 — directory is a "Mini Motorway"-style card grid

The 2026-05-31 "one unified table" note flattened the home everywhere and lost the
**"Mini Motorway"-soft card** thesis (§"Design thesis", §"Shape & space", Component #1).
Restored via `/design-review` as a **card grid** (user direction), reconciling both — still
every agency, no per-province grouping, but each is now a self-contained mini-page card:
- **`sm`+ (tablet/desktop):** a responsive **grid** (`sm:grid-cols-2 lg:grid-cols-3`) of
  vertical cards. Each card = name + province + mode chip (colour **and** label),
  a fixed **6-metric rank grid** (ridership · on-time · cost/rider · subsidy/rider · revenue ·
  fleet scale — ordinals only, `—` until sourced; chosen 2026-06-06/07, see notes below), and a drill button ("View full data →", or
  "Request this agency →" when unranked) to the detail page. `rounded-card` 18px, `shadow-soft`
  → `shadow-soft-hover`. This is the soft free mood.
- **`< sm` (phones):** one compact, dense **list** (mode bar · name · province · up to two
  peek ranks · chevron), each row tapping through to the detail page. Denser is better on a
  phone (the L1-list intent).

**Interaction change:** expand-in-place (wireframes-v5) is **replaced** by the drill button —
"go deeper" now navigates to the detail page rather than expanding in the list. Free payload
stays **rank-only** (no raw numbers reach the client); tokens and N<5 suppression unchanged.
`agency-row.tsx` (the old expand row) was removed; see `agency-card.tsx` + `agency-list-row.tsx`.

## Status update 2026-06-07 — card metric set finalized

The card's six free metrics are **Ridership · On-time · Cost/rider · Subsidy/rider · Revenue ·
Fleet scale** (`agency-card.tsx` `METRIC_SLOTS`) — a clean 3×2 grid. This supersedes the earlier
ridership/revenue/**farebox**/cost-per-rider/service-hrs/**fleet** list, implemented before the set
was chosen. Decisions (user-driven): **farebox** dropped (tells the same story as subsidy — pick
one); raw **fleet size** dropped (a metro car and a bus each count as "1") and **replaced by
"Fleet scale"** — a mode-weighted vehicle count (bus 1 · streetcar 2 · light-rail 3 · subway 4 ·
commuter-rail 5; BRT/trolleybus 1; ferry/paratransit/on-demand excluded). Weights live on
`core.modes.capacity_weight`; `fleet_capacity` is **`is_derived=false`** and its values are produced
by the cross-mode `mode_weighted_fleet` aggregation (the period_rollup pattern, NOT a within-period
equation), so it stays neutral — a "how big" number, no good/bad grade.

A **safety/complaint 6th metric was investigated and rejected**: no national, standardized,
agency-level source exists (US has the mandatory National Transit Database; Canada does not). The
closest, StatCan police-reported crime (UCR), is by *census metropolitan area* — city-level not
agency-level, big-CMAs only (N<5), crime-framed (clashes with the neutral-ordinal rule). Fleet
scale was chosen instead: sourceable from annual reports and neutral.

## Status update 2026-06-07 — per-agency calendar-year time-series template

Storage stays **atomic** (one `core.metric_values` row per value, tagged by reporting period +
mode) — the template is a **presentation/entry layer, not a storage change** (atomic storage is
what preserves the freedom to re-arrange later; per-agency tables would break cross-agency
ranking). The data-entry workbook (`ingest/workbook.py`) is now **one tab per agency**, laid out by
calendar year: `M1 M2 M3 Q1 … Q4 → YTD → Year`, where Q/YTD/Year are read-only computed roll-ups
(Excel `SUM` formulas in-sheet; the authoritative DB roll-up is `jobs/rollup.py` →
`calendar_rollup_metric`, which sums sourced months → quarter / YTD / annual_calendar, cited, never
overwriting a sourced value). The detail page's **Trends tab**
(`web/src/components/detail/trends-grid.tsx`, paid-only) renders the same grid. **Calendar year**
(fiscal-only annual figures are shown separately, never forced into a calendar cell).
