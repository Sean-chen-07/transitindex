# TransitIndex — Metric Standards Review (design review, no code changes)

**Version:** 1.0 | **Status:** Review (2026-06-14) | **Author:** metric design review
**Scope:** This decides what the metric SET *should* be. It changes no code. It judges every
metric in `refdata.METRICS` against a recognized external standard, reconstructs the financial
statements the set implies, tests every accounting identity, and proposes the additions that
close the gaps.

**Files verified for this review (not assumed):**
`ingest/transitindex_ingest/refdata.py` (the 32-metric `METRICS`, `NON_RANKABLE_METRICS`,
`MODE_CAPACITY_WEIGHT`) · `metric_dictionary.yaml` (Is/Is-NOT/Includes/Excludes) ·
`equations.py` (the identity graph + solver) · `validation/flags.py` (which identities are
*enforced*) · `jobs/rank_refresh.py` + `jobs/derived_recompute.py` + `jobs/bulk_load.py` (what
actually gets ranked) · `contract.py` (`MetricValueRecord` — the dimensions a value can carry) ·
`pdf/llm.py` (the `basis` field) · `docs/planning/balance-sheet-and-frequency-plan.md` (PSAB
design intent) · `docs/reference/data-dictionary.md` (generated view).

**Standards used as the yardstick (cited per judgment):**
- **CUTA** — Canadian Urban Transit Association *Canadian Transit Fact Book* operating-data
  conventions. CUTA's "direct operating expenses" are a **cash-operating** basis that
  **excludes amortization/depreciation**.
- **NTD** — US National Transit Database. Defines **Unlinked Passenger Trips (UPT)**, **Vehicle
  Revenue Hours/Miles (VRH/VRM)**, operating expense by function/object — also **excludes
  depreciation** from operating expense.
- **PSAB / PS 1201** — Canadian public-sector accounting *Statement of Financial Position* and
  the **net-debt model**. The CICA/PSAB *Indicators of Financial Condition* (sustainability /
  flexibility / vulnerability) are the recognized public-sector ratio set.

**The one principle behind every judgment:** *a metric named X must contain X for every agency,
every year.* A bigger or more capital-heavy agency is not an exception to be smuggled into an
operating metric — its scale must land in the metric **designed** to show scale (capital, debt,
assets, amortization, or an explicit enterprise-total lens), never inside an operating number.
Pinning the boundary should sometimes make an agency look **worse** than its own headline (e.g.
amortization-in lowers farebox recovery) — that is the boundary doing its job.

---

## Executive summary (the load-bearing findings)

1. **`operating_expenses` has no pinned basis, and no structured field to record one.** The
   dictionary says "record which basis the source used (PSAB includes amortization, CUTA
   excludes it)" — but `MetricValueRecord` has **no `basis` dimension** for this (its `basis`
   field means actual/budget/forecast/restated; `service_scope` means conventional/specialized).
   So two agencies can sit in the same ranked cohort on **different** expense bases, and the
   difference is invisible to ranking. This silently corrupts **farebox_recovery_ratio**,
   **cost_per_rider**, **cost_per_hour**, and **subsidy_per_rider** — the four ratios the
   product most wants to be comparable. **Highest-priority fix.**

2. **The expense components cannot sum to the total, yet the identity is enforced.**
   `expense_components` requires `labour + energy + materials = operating_expenses`. There is
   **no amortization line and no "other" residual**. For any real PSAB statement (amortization
   in) or any agency with insurance/purchased-transportation/taxes (an "other" object), the
   three components fall short — so the enforced `sum_mismatch` either **false-flags** honest
   data or **pressures the extractor to mis-bucket** amortization/other into one of the three.
   **Add `amortization` and `other_operating_expenses`.**

3. **The set cannot bridge the two financial statements.** There is no `annual_surplus_deficit`,
   so `accumulated_surplus(end) = accumulated_surplus(start) + annual surplus/deficit` cannot be
   tested. And `total_operating_subsidy = operating_expenses − operating_revenue` (enforced)
   silently assumes the **annual result is zero**, which is generally false. **Add
   `annual_surplus_deficit`** (it also makes the operating-gap identity honest).

4. **`fleet_capacity` ("Fleet scale") is invented and its weights are not capacity.** The
   integer weights (bus 1 … commuter_rail 5) are not grounded in seats or design capacity and
   no agency reports the figure. It also carries `is_derived=False` despite being a cross-mode
   aggregation. **Decided: dropped — replaced by a non-ranked 4-class fleet composition
   (Bus · Light rail · Heavy rail · Commuter rail).**

5. **The "size, not performance → don't rank" rule is applied only to balance-sheet stocks.**
   `operating_revenue` (a raw dollar) is *ranked* by the StatCan loader; `capital_expenditure`,
   `fleet_size`, and `fleet_capacity` are rankable size metrics. The principle is sound; it is
   just drawn at "balance sheet" instead of at "size vs performance." **Decided: rate only the
   five hero boxes; everything else view-only.**

6. **`on_time_performance` is ranked but is not a standard and is self-defined per agency.**
   Neither CUTA nor NTD standardizes OTP; each agency picks its own on-time window. Ranking it
   across agencies compares incommensurable definitions. **Decided: it stays a rated hero box;
   open whether to footnote "definitions vary" or drop just its rank badge.**

7. **Doc/enforcement drift to clean up:** `data-dictionary.md` is stale (31 metrics, missing
   `fleet_capacity`); the net-debt identity and the component-bounds checks promised in the
   balance-sheet plan are enforced only in `equations.py` (or not at all), not in
   `flags.py`/`validate_cohort`.

The single highest-value *addition* is an explicit **enterprise/total lens** (`total_revenue`,
`total_expenses`, `annual_surplus_deficit`, `amortization`) measured the same way for every
agency — it honours "a bigger agency should look bigger" **and** closes findings 2 and 3, while
keeping the operating metrics narrow and comparable.

---

## Decisions taken (2026-06-14, user)

These override the recommendations below where they conflict.

1. **Ranking — only the Highlights hero boxes are rated.** After dropping fleet (see #2), the
   rated set is **five**: `ridership`, `operating_revenue`, `on_time_performance`,
   `cost_per_rider`, `subsidy_per_rider`. **Every other metric is shown without a rank** — the
   efficiency ratios (`farebox_recovery_ratio`, `cost_per_hour`, `trips_per_revenue_hour`,
   `average_fare`), every service/fleet fact, and **all** balance-sheet metrics. This **retires
   the two ranked balance-sheet ratios** (`debt_to_assets`, `net_debt_per_capita`) from ranking,
   superseding `balance-sheet-and-frequency-plan.md` §2/§3. *Implementation:* set
   `comparable_flag=False` for every non-rated metric (or restrict every `rank_metric_codes` list
   to the five) — instead of relying on `NON_RANKABLE_METRICS`, which only covers balance-sheet
   dollars today. *Downstream:* the Highlights hero grid drops to 5 boxes — leave it at five or
   promote another metric into the 6th slot (which would then be rated) — a
   `detail-view-metrics.md` layout call, not a metric one.
   - **Open tension (flagged, pending user call):** `on_time_performance` is rated but is the one
     metric whose definition differs per agency (each picks its own on-time window), so its rank
     does not compare like with like. Recommended: keep it as a hero *number* but either footnote
     "definitions vary" or drop just its rank badge. `ridership` and `operating_revenue` are
     intentional "biggest" leagues and are fine as neutral ordinals.

2. **Fleet — drop the weighted "fleet scale" metric; show a labeled composition instead.**
   `fleet_capacity` and `MODE_CAPACITY_WEIGHT` are **removed** — the integer weights were
   arbitrary, and any per-vehicle weighting is hostage to train-length / car-vs-trainset
   reporting. Replace with a **non-ranked breakdown** across four capacity-ordered classes, each a
   plain labeled count: **Bus** (bus, BRT, trolleybus) · **Light rail** (LRT, streetcar) ·
   **Heavy rail** (grade-separated rapid transit — Toronto subway, Montréal Métro, SkyTrain) ·
   **Commuter rail** (GO, exo, West Coast Express). **Count by trains for rail** (user's call —
   simpler than cars), by vehicle for bus; ferries/paratransit/on-demand excluded (or ferries get
   their own line). Reuses the existing per-mode `fleet_size` (already mode-dimensioned), grouped
   into the four classes — **no new weighted metric**. Labels follow NTD ("heavy rail" =
   subway/metro; "commuter rail" = GO-type).

3. **Approved as proposed:** the five additions (`amortization`, `annual_surplus_deficit`,
   `total_revenue`, `total_expenses`, `other_operating_expenses`, plus `asset_consumption_ratio`),
   and pinning `operating_expenses` to the amortization-excluded basis and `operating_revenue` to
   earned-only.

4. **Revenue section = five lines (user, final 2026-06-14; supersedes the four-bucket note, the
   "Total operating revenue" subtotal, and Decision #3's strict "earned only" pin on
   `operating_revenue`).** Show: **Farebox revenue** (`passenger_fare_revenue`) + **Other revenue**
   (`other_revenue`, the broad non-fare/non-subsidy catch-all) = **Total revenue excluding subsidy**
   (`operating_revenue` ★); then **+ Subsidy** (`total_operating_subsidy`) **= Total revenue**
   (`total_revenue`). Ties out with **no residual**: `operating_revenue` is *defined* as
   `total_revenue − total_operating_subsidy`, which is exactly the StatCan 23-10-0307 line ("Total
   revenue, excluding subsidies") — so the StatCan mapping becomes definitionally exact (it removes
   the latent mismatch A.5 flagged, where StatCan gives "all but subsidy" but the metric was pinned
   to "earned only"). **Consequence:** the earned subtotal is now "all revenue except subsidy"
   (ancillary + any capital/investment income included), broader than strict operating. To keep the
   rider-share ratios honest (landmine 1), **`farebox_recovery_ratio` and `average_fare` take
   `passenger_fare_revenue` as the numerator**, not the broad `operating_revenue`. `farebox` is
   sourced from the PDFs; `other_revenue` is the residual (`operating_revenue − farebox`).
   `other_operating_revenue` is dropped (not needed).

5. **Metric naming = the statement line (user, 2026-06-14).** Rename each revenue code to read like
   its displayed line: `passenger_fare_revenue` → `farebox_revenue`; `operating_revenue` →
   `total_revenue_excluding_subsidy` (matches the StatCan 23-10-0307 measure label verbatim);
   `total_operating_subsidy` → `subsidy`. References to the old codes elsewhere in this review (the
   Part A/D analysis) mean the renamed metric. The rename (live codes → DB migration + parity +
   adapter + ratios + web + tests) is specified in the build plan.

---

# Part A — Does each metric follow a recognized standard?

Map → CUTA / NTD / PSAB / INVENTED. "Same boundary for all?" asks whether the in/out line can be
drawn identically for every agency and year. Depth is concentrated on the load-bearing metrics;
clean metrics get a shorter pass.

## A.0 Summary table

| Metric | Maps to | Conforms | Same boundary for all? | Headline issue |
|---|---|---|---|---|
| ridership | NTD UPT (CUTA passenger trips) | **yes** | yes (with unlinked rule held) | linked-vs-unlinked drift; ranked as size |
| revenue_service_hours | NTD VRH / CUTA RVH | **yes** | mostly | deadhead exclusion must hold |
| vehicle_revenue_km | NTD VRM / CUTA RVK | **yes** | mostly | same as above |
| on_time_performance | none (not in CUTA/NTD) | **no** | **no** | self-defined window; should not be ranked |
| operating_revenue | CUTA/NTD operating revenue | **partial** | **at risk** | "operating" vs "total" boundary; fares vs ancillary; One Fare |
| operating_expenses | CUTA/NTD operating expense | **partial** | **NO** | **amortization in/out not pinned** |
| total_operating_subsidy | CUTA operating funding | partial | at risk | breaks when annual result ≠ 0 |
| labour_cost | CUTA/NTD object class | yes | mostly | contracted labour boundary |
| energy_fuel_cost | CUTA/NTD object class | yes | mostly | facility vs traction energy |
| materials_services_cost | CUTA/NTD object class | partial | at risk | absorbs the missing "other" |
| farebox_recovery_ratio | CUTA/NTD R/C | partial | **inherits expense basis** | numerator/denominator basis must match |
| cost_per_rider | CUTA/NTD | partial | inherits expense basis | amortization-in inflates it |
| cost_per_hour | CUTA/NTD | partial | inherits expense basis | same |
| subsidy_per_rider | CUTA-derived | partial | inherits subsidy identity | same |
| average_fare | CUTA/NTD (fares/UPT) | partial | numerator is *operating* rev, not fares | slight overstatement |
| fleet_size | NTD VOMS / total fleet | partial | **no** (bus vs rail car units) | unit-mixing; ranked as size |
| fleet_average_age | NTD fleet age | yes | partial | mode-mix lifespans |
| accessible_fleet_pct | (AODA/policy, not CUTA/NTD) | yes | yes | low discriminating power |
| fleet_capacity ("Fleet scale") | **INVENTED** | **no** | n/a | arbitrary weights; `is_derived=False` but derived |
| capital_expenditure | CUTA capital / PSAB TCA additions | yes | mostly | ranked as size; no per-rider companion |
| total_financial_assets | PSAB | yes | yes | — |
| total_liabilities | PSAB | yes | yes | — |
| total_non_financial_assets | PSAB | yes | yes | — |
| total_assets | PSAB (identity) | yes | yes | — |
| tangible_capital_assets | PSAB TCA (net) | yes | yes | net vs gross must hold |
| accumulated_surplus | PSAB (identity) | yes | yes | — |
| long_term_debt | PSAB subset | yes | mostly | LTD vs total-liab confusion |
| cash_and_investments | PSAB subset | yes | mostly | — |
| net_debt | PSAB net-debt model | **yes** | yes | size dollar — correctly not ranked |
| debt_to_assets | **adapted** (corporate, not PSAB) | partial | yes | PSAB indicator is net-debt-to-revenue |
| net_debt_per_capita | PSAB/CICA indicator | **yes** | yes (static pop) | the right civic headline |

## A.1 Ridership — NTD Unlinked Passenger Trips · conforms

1. **Question / for whom.** "How many trips did this system carry?" — the public/council
   headline of demand.
2. **Boundary.** Unlinked boardings: one count per vehicle boarding, transfers and pass/free
   riders included. This is exactly **NTD UPT**; CUTA's "regular service passenger trips" is the
   close cousin (CUTA historically blends in some transfer conventions, so NTD is the cleaner
   anchor). The dictionary draws the line correctly (Is-NOT: distinct riders, linked journeys).
3. **Steelman the other boundary.** If we counted **linked** journeys instead, a TTC trip with a
   subway-to-bus transfer would count once, not twice — TTC's number would fall ~20–30% and a
   transfer-heavy network would rank below a no-transfer network that carries fewer *people*.
   Unlinked wins: it is the supply-neutral, internationally standard count and it is what every
   open-data/StatCan feed actually publishes. Conceded only edge: comparing a heavy-transfer
   network to a coverage network slightly flatters the former — acceptable and disclosed.
4. **Same boundary for all?** Yes **if** the unlinked rule holds. Real drift risk: some agencies
   publish "revenue passengers" (excludes free/transfers) — the dictionary's confusion list
   catches this. The YTD-stored-as-monthly trap is also handled (it is excluded explicitly).
5. **Visible / invisible.** Makes demand visible; hides demand *quality* (crowding, pass-ups)
   and distinct reach (how many *people*). Acceptable; distinct riders are not reportable.

*Ranking note:* ridership is ranked `higher_is_better=True`. It is a **size** metric (TTC ~700M
vs Burlington ~2M). Ranking "who carries the most" is a defensible civic comparison, but be
honest it is a *biggest*, not *best*, leaderboard — see §A-rank.

## A.2 Revenue service hours · A.3 Vehicle revenue km — NTD VRH/VRM · conform

Same shape, judged together. Question: "how much service was *supplied*?" — the denominator of
every productivity and unit-cost ratio. Boundary = **in-revenue-service only**, excluding
deadhead/pull-in-out, layover-where-defined-out, training, maintenance moves. This is exactly
NTD VRH/VRM and CUTA Revenue Vehicle Hours/Km. Steelman "total vehicle hours" (include
deadhead): it would reward agencies with long garage-to-route distances for *non-productive*
travel and inflate the denominator unevenly (sprawling systems deadhead more), making
cost-per-hour *look* better for the least efficient. Revenue basis wins decisively. Drift risk:
"platform hours"/"total vehicle hours" mislabeled as revenue hours — the dictionary names this.
Same boundary drawable for all. Correctly **neutral** (`higher_is_better=None`) — more service
is neither good nor bad without context.

## A.4 On-time performance — INVENTED relative to CUTA/NTD · does NOT conform · **rated (hero box) — flagged**

1. **Question / for whom.** "Is the service reliable?" — rider-facing quality.
2. **Boundary.** "% of trips meeting *the agency's own* on-time definition." The Is-NOT openly
   admits "NOT a single universal standard."
3. **Steelman.** Could a council compare two agencies' OTP? Only if the on-time *window* matched.
   It does not: bus is commonly "0 to +3 min" or "−1 to +3"; rail is often headway/±1 min;
   some count by stop, some by trip, some by terminal departure. A 90% at ±1 min is a far harder
   achievement than 90% at +5 min. There is **no boundary that is the same for all agencies** —
   the metric's own definition makes it agency-relative.
4. **Same boundary for all?** **No.** This is the cleanest "cannot be standardized" case in the
   set. Neither CUTA nor NTD collects OTP for exactly this reason.
5. **Consequence.** `on_time_performance` is `higher_is_better=True`, `comparable_flag` defaults
   True, and `compute_ranks` will rank it. So the product currently produces a **cross-agency
   OTP ranking built from incommensurable definitions** — a skeptical councillor with two annual
   reports open will dismantle it in one sentence.

**Decision (2026-06-14).** OTP **stays rated** — it is one of the five Highlights hero boxes, and
the rule is "only hero boxes are rated." The standards judgment stands: it is the one rated metric
whose definition is agency-relative, so its rank is the least like-for-like in the set. **Open
sub-decision (pending):** keep the rank with a "definitions vary by agency" footnote, **or** keep
OTP as a hero *number* but drop just its rank badge (an exception that would take the rated set to
four). Either way, **record each agency's on-time window in a structured field, not just notes**, so
the displayed number is auditable. (A truly comparable reliability metric would need a
TransitIndex-defined window over raw AVL/GTFS-RT data — out of scope.)

## A.5 operating_revenue — CUTA/NTD operating revenue · partial · boundary at risk *(landmine 1)*

1. **Question / for whom.** "How much does the service *earn* on its own?" — the numerator of
   farebox recovery and the honest counterweight to subsidy.
2. **Boundary.** Earned operating revenue = passenger fares + ancillary operating income
   (advertising, charter, fees); **excludes** all government operating subsidy and **all**
   capital/construction grants and contributions. This matches CUTA/NTD "operating revenue" and
   is the correct line.
3. **Steelman the broad boundary (an agency's "total revenue").** Take Metrolinx: its PSAB
   statement of operations shows **~$770M+** of revenue because, under PSAB, provincial
   *operating* transfers and the **amortization of deferred capital contributions** are
   recognized as revenue, alongside fares and (in build years) construction-related recoveries.
   If we let "operating revenue" drift toward that "total revenue":
   - the **number** balloons for transfer-heavy/enterprise agencies (Metrolinx, TransLink) and
     barely moves for fare-reliant ones (TTC) — incomparable inputs;
   - **farebox_recovery_ratio = operating_revenue / operating_expenses** would jump toward (or
     past) 100% for Metrolinx purely because subsidy was counted as "earned" — the ratio would
     **stop meaning "share paid by riders"** and start meaning nothing;
   - **average_fare = operating_revenue / ridership** would explode for the same reason;
   - a council reader would **conclude Metrolinx is nearly self-funding**, the opposite of true.
   The narrow boundary wins unambiguously. Metrolinx's enterprise scale is real and deserves to
   be *seen* — but in a **companion `total_revenue` metric** (Part D), never inside
   `operating_revenue`.
4. **Same boundary for all? At risk on three seams:**
   - **fares-only vs fares+ancillary.** The metric is the broader earned figure (correct), but
     `average_fare` then divides *operating* revenue (incl. advertising/charter) by ridership,
     so it slightly **overstates** the true per-rider fare. Minor; a fares-only line fixes it.
   - **One Fare / program-funded fares (2024+).** Ontario's One Fare reimburses agencies for
     fares forgone on cross-boundary transfers; U-Pass and similar bulk programs are
     province/institution-funded. If agency A books the reimbursement as **fare revenue** and
     agency B books it as **subsidy**, their operating_revenue (and farebox recovery) diverge
     for an accounting choice, not a real difference. This is a live, growing drift.
   - **Construction / intercompany recoveries** at build-heavy agencies must be excluded; the
     dictionary should name them in Is-NOT.
5. **Visible / invisible.** Makes "earned income" visible; hides enterprise scale (by design) →
   feed `total_revenue` in Part D; hides the earned-fare-vs-program-fare split → feed
   `passenger_fare_revenue` in Part D.

*Ranking note:* `bulk_load.py` passes `operating_revenue` to `bulk_refresh_ranks`, so this raw
dollar **is ranked** — i.e. a size leaderboard. See §A-rank.

## A.6 operating_expenses — CUTA/NTD operating expense · partial · **boundary NOT the same for all** *(landmine 2 — the big one)*

1. **Question / for whom.** "What does it cost to run the service?" — denominator of farebox
   recovery and every unit-cost ratio; the most consequential single definition in the set.
2. **Boundary — and the unresolved fork.** CUTA *and* NTD both define operating expense on a
   **cash-operating basis that EXCLUDES amortization/depreciation**. But the **source** for most
   agencies is the **PSAB audited statement of operations, which INCLUDES amortization**. The
   dictionary acknowledges the fork and says *"record which basis the source used."* The problem:
   **there is nowhere structured to record it.** `MetricValueRecord` has `service_scope`
   (conventional/specialized/total) and the PDF row has `basis` (actual/budget/forecast/
   restated) — neither captures amortization-in vs amortization-out. The basis ends up in
   free-text `notes`, and **ranking ignores notes**. So the ranked cohort can mix bases.
3. **Steelman each side, with the numbers moved.** Take TTC-scale figures (illustrative):
   fares ≈ \$1.2B; operating expense **ex-amortization** ≈ \$1.9B; amortization ≈ \$0.5B; so
   operating expense **incl-amortization** ≈ \$2.4B.
   - **CUTA basis (exclude amortization):** farebox = 1.2 / 1.9 = **63%**; cost_per_rider on the
     ex-amortization base.
   - **PSAB basis (include amortization):** farebox = 1.2 / 2.4 = **50%**; cost_per_rider ~26%
     higher.
   A **13-point farebox swing and a double-digit cost-per-rider swing from an accounting choice
   alone.** If TTC is on CUTA basis and Metrolinx on PSAB basis in the same ranked cohort, the
   ranking is an artefact of bookkeeping, not performance.
   - *Which basis should win?* For **cross-agency comparability**, anchor to the **CUTA/NTD
     operating basis (EXCLUDE amortization)** — it is the recognized transit-operating standard
     and it isolates the controllable cost of running service. But do **not** discard
     amortization: extract it as **its own line** (Part D) so the operating-basis figure is
     `PSAB total operating expense − amortization`, fully auditable, and the capital-consumption
     cost is still visible. Standardizing this way will **lower** the reported farebox of
     agencies that publish a flattering ex-amortization headline only if they were *excluding*
     other costs — i.e. it makes everyone honest on the same line.
4. **Same boundary for all? No** — today it depends on each source's accounting basis, with no
   field to normalize on. **This is the top fix.**
5. **Second-order map (trace explicitly).** `operating_expenses` flows into
   `farebox_recovery_ratio` (denominator), `cost_per_rider` (numerator), `cost_per_hour`
   (numerator), and — via `total_operating_subsidy = operating_expenses − operating_revenue` —
   into `subsidy_per_rider`. A basis error here mis-ranks **four** headline ratios at once.

**Recommendation.** (i) Pin the ranked definition to **operating basis, amortization excluded**
(CUTA/NTD). (ii) Add an `amortization` metric and an `other_operating_expenses` residual (Part
D) so the basis is reconstructable and the components close. (iii) Add a structured
**`cost_basis` dimension** (`operating` | `psab_total`) to the value contract so a PSAB-basis
figure is never silently ranked against a CUTA-basis one — at minimum, set `comparable_flag=False`
when the basis can't be normalized.

## A.7 total_operating_subsidy — CUTA operating funding · partial

Question: "how much public money covers the gap?" Boundary: combined municipal+provincial+
federal **operating** contributions, excluding capital grants — matches CUTA "operating
funding." The Is-NOT correctly excludes capital. **The fragility:** the dictionary and the
enforced identity treat it as `operating_expenses − operating_revenue`, which is only true when
the **annual surplus/deficit is zero**. In real PSAB statements the bottom line is rarely zero
(deferred capital contributions amortized into revenue, carbon-credit/gas-tax timing, one-time
program funding). So the identity is an **approximation presented as an identity**. Same boundary
mostly drawable, but the gap-closure assumption needs `annual_surplus_deficit` (Part D) to be
honest. Direction correctly **neutral**.

## A.8 labour / A.9 energy / A.10 materials — CUTA/NTD object classes · conform (with a residual gap)

These are the CUTA/NTD **expense-by-object** classes. Individually each boundary is clean:
labour = all-staff wages+benefits (contracted labour excluded → sits in materials/services);
energy = traction fuel+electricity (facility energy excluded unless bundled); materials =
parts/supplies + purchased/contracted services. The **collective** problem is structural, not
per-metric: CUTA/NTD object breakdowns also include **amortization** and an **"other"** class
(insurance/casualty, purchased transportation, taxes, misc). With only three of the classes
present, `materials_services_cost` becomes a magnet for whatever doesn't fit, drifting agency to
agency. This is the Part B `expense_components` failure. Fix = add `amortization` +
`other_operating_expenses`.

## A.11 farebox_recovery_ratio · A.12 cost_per_rider · A.13 cost_per_hour — CUTA/NTD · partial (basis-inherited)

All three are standard CUTA/NTD efficiency ratios and the *formulas* are right
(`operating_revenue/operating_expenses`, `operating_expenses/ridership`,
`operating_expenses/revenue_service_hours`). They are only as comparable as their inputs: every
one inherits the **A.6 amortization-basis** problem (and farebox also inherits A.5's
numerator-boundary problem). No independent issue — fixing A.5/A.6 fixes all three. Directions
correct (farebox neutral — context-dependent; the two unit costs `lower_is_better`).

## A.14 subsidy_per_rider — CUTA-derived · partial

`total_operating_subsidy / ridership`, equivalently `(expenses − revenue)/ridership`. Standard
and useful ("public cost per boarding"). Inherits A.6 (basis) and A.7 (annual-result-zero
assumption). Correctly neutral.

## A.15 average_fare — CUTA/NTD (fares ÷ UPT) · partial

Formula is `operating_revenue / ridership`. CUTA/NTD "average fare" uses **fare revenue ÷ UPT**;
this uses the **broader operating revenue** (incl. advertising/charter), so it reads slightly
**high** versus a true average fare, and the gap varies with how much ancillary income each
agency books. Defensible as "average operating revenue per boarding," but the label "average
fare" implies fares. A `passenger_fare_revenue` line (Part D) would let this use a fares-only
numerator and match the standard.

## A.16 fleet_size — NTD VOMS / total fleet · partial · unit boundary not the same for all

Question: "how big is the fleet?" Boundary: active **revenue** vehicles, excluding
non-revenue/stored/retired — matches NTD "total fleet"/VOMS conventions. The unavoidable seam:
**a bus and a metro car are different units.** The dictionary says "note whether rail is counted
by car or trainset," but the stored value is a single undifferentiated count. So TTC's
(buses + streetcars + subway cars) is summed into one number that is not commensurable with a
bus-only agency's count. Same boundary **not** cleanly drawable across mixed-mode agencies.
Per-mode `fleet_size` exists in the model, and per the 2026-06-14 decision it becomes the source
for the four-class fleet breakdown (Bus · Light rail · Heavy rail · Commuter rail) that
**replaces** `fleet_capacity`. Shown, **not rated** (decision #1).

## A.17 fleet_average_age — NTD fleet age · conforms (mode caveat)

NTD reports average fleet age; this matches. Boundary clean (active revenue fleet). Caveat:
averaging across modes with very different service lives (bus ~12y, rail ~30y+) blends a "young
bus / old train" agency into a midpoint that hides both — the dictionary names this. `lower_is_
better` is right as a state-of-good-repair signal. Per-mode would be more honest but is a
display refinement, not a definition error.

## A.18 accessible_fleet_pct — policy metric (not CUTA/NTD) · conforms but low-signal

A clean ratio (accessible revenue vehicles ÷ active revenue fleet). Not a CUTA/NTD comparability
metric; it is a policy/AODA-style indicator. Boundary is the same for all and easy to source.
The honest caveat: in Canada most conventional bus fleets are at or near 100% low-floor, so the
metric has **low discriminating power** and a ranking on it mostly produces ties at ~100%. Keep
it as a shown fundamental; expect it to rarely move a ranking.

## A.19 fleet_capacity ("Fleet scale") — INVENTED · does NOT conform · **DROPPED (decided)**

1. **Question it claims to answer.** "How big is the fleet once you stop pretending a subway car
   equals a bus?" — a fair concern.
2. **Boundary / method.** `Σ capacity_weight × fleet_size(mode)` with integer weights bus 1,
   streetcar 2, light_rail 3, subway 4, commuter_rail 5 (BRT, trolleybus 1; ferry/paratransit/
   on-demand excluded). **No external standard** defines this — not CUTA, not NTD, not PSAB.
3. **Steelman / refute.** Does the weighting reflect reality? A 40-ft bus seats ~40 (crush ~60);
   an articulated bus ~60; a TTC subway car carries ~130 seated and far more at crush; a GO
   commuter coach ~160+ seated (bilevel). So real capacity ratios are roughly bus 1 : subway
   3–4+ : commuter coach ~4. The weights are *plausible in rank order* but the integers are not
   measured capacity, the per-vehicle truth varies by rolling stock, and the metric is a
   **weighted count, not capacity** (its own Is-NOT admits "NOT seated capacity"). So it neither
   conforms to a standard nor measures what its name ("Fleet scale" / capacity weight) implies.
4. **Same boundary for all?** Only in the trivial sense that the weight table is fixed. But the
   table is an editorial choice (migration 015) that could move and silently re-rank everyone.
5. **Two further inconsistencies.** (a) It carries `is_derived=False` in `refdata` despite being
   a derivation (`MODE_WEIGHTED_FLEET`), so the equation graph and the `is_derived` flag both
   hide its computed nature. (b) Like all size metrics it is **not** in `NON_RANKABLE_METRICS`,
   so it is rankable — but ranking an invented weighted count is the weakest leaderboard in the
   set.

**Decision (2026-06-14).** **Drop `fleet_capacity` and `MODE_CAPACITY_WEIGHT` entirely.** The
integer weights are arbitrary, and any per-vehicle weighting is hostage to train-length /
car-vs-trainset reporting (a 5-car and a 10-car train each count as "one train" unless you count
cars, and agencies report inconsistently). Replace with a **non-ranked, labelled fleet
composition** built from the existing per-mode `fleet_size`, grouped into four capacity-ordered
classes — **Bus** (bus, BRT, trolleybus) · **Light rail** (LRT, streetcar) · **Heavy rail**
(grade-separated rapid transit — Toronto subway, Montréal Métro, SkyTrain) · **Commuter rail**
(GO, exo, West Coast Express) — each a plain count, **counted by trains** for rail (user's call),
by vehicle for bus. Ferries/paratransit/on-demand excluded (ferries may get their own line).
Labels follow NTD ("heavy rail" = subway/metro; "commuter rail" = GO-type). No invented weights,
no single collapsed number.

## A.20 capital_expenditure — CUTA capital / PSAB TCA additions · conforms

Clean flow definition (actual capital spent on long-lived assets; excludes amortization and the
budget/plan). Matches CUTA capital reporting / PSAB TCA additions. Per the 2026-06-14 ranking
decision it is **not rated** (only the five hero boxes are), which resolves the old "size dollar
ranked as if it were quality" concern. A comparable companion (`capex_per_rider` or capex as a
share of operating expense) is deferred — see Part D.5.

## A.21–A.31 Balance-sheet family — PSAB / PS 1201 · conform (one adaptation)

The eight sourced line items and `net_debt`/`accumulated_surplus`/`total_assets` follow the
**PSAB net-debt model** exactly, and the identities hold (verified in Part B). Specifics:
- `total_financial_assets`, `total_liabilities`, `total_non_financial_assets`, `total_assets`,
  `tangible_capital_assets` (net book value), `accumulated_surplus`, `long_term_debt`,
  `cash_and_investments` — all standard PSAB statement-of-financial-position lines, same boundary
  for all, correctly **non-rankable** (size).
- `net_debt = total_liabilities − total_financial_assets` — **the** PSAB indicator, sign
  convention correct (positive = net debt; negative = net financial assets). Derived for the
  cross-check, correctly non-rankable. Conforms fully.
- `net_debt_per_capita` — a recognized **CICA/PSAB *Indicator of Financial Condition*** (net debt
  to population). Standards-wise the right civic headline; static service-area population is a
  reasonable, stable denominator (label "per resident served"). **Per the 2026-06-14 decision it is
  no longer ranked** (only the five hero boxes are) — shown as a value on the Financials tab.
- `debt_to_assets = total_liabilities / total_assets` — **adapted, not PSAB.** This is a
  corporate leverage ratio; the PSAB sustainability ratio is **net-debt-to-(total annual
  revenue)** or net-debt-to-GDP, plus the **asset-consumption ratio** (accumulated amortization ÷
  gross cost of TCA) for state-of-good-repair. `debt_to_assets` is defensible and scale-free.
  **Neither balance-sheet ratio is ranked any longer** (2026-06-14 decision); if a balance-sheet
  leverage ratio is ever promoted to a rated hero box, the standards-anchored choice is
  **net-debt-to-revenue**, not `debt_to_assets` (Part D).

## A-rank — the cross-cutting ranking inconsistency

`rank_refresh.compute_ranks` ranks any value with `comparable_flag=True`; `comparable_flag` is set
to `code not in NON_RANKABLE_METRICS` only in `workbook.py` and `derived_recompute.py`, and
`NON_RANKABLE_METRICS` holds **only the nine balance-sheet dollars**. Consequence: the principle
*"a dollar/size figure measures size, not performance, so don't rank it"* — explicitly stated for
the balance sheet — is **not** applied to the equally size-like `operating_revenue` (actually
ranked by the StatCan loader), `operating_expenses`, `capital_expenditure`, `fleet_size`, or
`fleet_capacity`. Ridership is also a size metric, ranked deliberately.

**Decided (2026-06-14):** only the five Highlights hero-box metrics are rated — `ridership`,
`operating_revenue`, `on_time_performance`, `cost_per_rider`, `subsidy_per_rider`. Everything else
is shown without a rank. This is the uniform rule the section called for: `ridership` and
`operating_revenue` are kept as intentional "biggest" leagues (neutral ordinals); every other size
dollar, count, and balance-sheet figure is view-only. *Implementation:* drive ranking off the
hero-box set (`comparable_flag=False` for everything else), not the current `NON_RANKABLE_METRICS`
list (which only covers balance-sheet dollars). See the build plan.

---

# Part B — Do the metrics articulate into proper financial statements?

**First, the requester's mental model, gently corrected.** The instinct *"if I add up all the
expenses, does it become total liabilities like a normal balance sheet?"* mixes the two
statements. **Expenses are flows** — they accumulate over a *period* (a year) and live on the
**Statement of Operations**. **Liabilities are stocks** — a snapshot at a single *instant* (fiscal
year-end) on the **Statement of Financial Position**. Adding up a year of expenses gives you the
**cost of running the service**, not what the agency *owes*. The two statements are linked, but not
by "expenses = liabilities." They are linked by the **annual result**:

> **accumulated_surplus(end of year) = accumulated_surplus(start of year) + (annual surplus or
> deficit)**, where **annual surplus/deficit = total revenue − total expenses** for the year.

That is the only bridge from the flow statement to the stock statement — and, as shown below, the
metric set **cannot build it yet** because it has no `annual_surplus_deficit`.

## B.1 Statement of Operations (flows) — reconstructable, with holes

From the set we can lay out:

```
  Operating revenue            operating_revenue                (earned: fares + ancillary)
  + Operating subsidy          total_operating_subsidy          (gov't operating transfers)
  ───────────────────────────
  Operating expenses           operating_expenses
     of which  Labour          labour_cost
               Energy/fuel     energy_fuel_cost
               Materials/svc   materials_services_cost
               Amortization    ——  MISSING ——
               Other           ——  MISSING ——
  ───────────────────────────
  Annual surplus / (deficit)   ——  MISSING ——                  (the bottom line)

  [memo] Capital expenditure   capital_expenditure              (a cash-flow / TCA-additions item,
                                                                 not part of operating result)
```

The set captures the top (revenue, subsidy) and the total expense, but **not** the full expense
decomposition and **not** the bottom line.

## B.2 Statement of Financial Position (stocks) — complete and closes

```
  Financial assets             total_financial_assets
  − Liabilities                total_liabilities
  ───────────────────────────
  = Net debt / (net fin. assets)  net_debt            (derived)
  + Non-financial assets       total_non_financial_assets   (of which tangible_capital_assets)
  ───────────────────────────
  = Accumulated surplus        accumulated_surplus
  [also]  total_assets = total_financial_assets + total_non_financial_assets
  [subsets] long_term_debt ⊂ total_liabilities ; cash_and_investments ⊂ total_financial_assets
```

This statement is **complete** and self-closing under PSAB.

## B.3 Identity pass/fail (and where it's enforced)

| # | Identity | Holds? | Enforced where | Notes |
|---|---|---|---|---|
| 1 | `total_assets = total_financial_assets + total_non_financial_assets` | **PASS** | `flags.py` (identity 3) + `equations.py` (`total_assets_identity`) | clean PSAB |
| 2 | `accumulated_surplus = total_assets − total_liabilities` | **PASS** | `flags.py` (identity 4) + `equations.py` | clean PSAB |
| 3 | `net_debt = total_liabilities − total_financial_assets` | **PASS** | `equations.py` only (`net_debt_def`) — **NOT in `flags.py`** | plan §2 claims a `sum_mismatch`; not in `validate_cohort` |
| 4 | `operating_expenses = labour + energy + materials + amortization + other` | **FAIL (cannot sum)** | `flags.py` enforces the **3-term** version | no amortization, no "other" → enforced identity is wrong |
| 5 | `total_operating_subsidy = operating_expenses − operating_revenue` | **CONDITIONAL** | `flags.py` (identity 2) + `equations.py` (`expense_revenue_subsidy`) | only true if annual result = 0; broken by deferred capital, carbon credits, program funding |
| 6 | `accumulated_surplus(end) = accumulated_surplus(start) + annual surplus/deficit` | **UNTESTABLE** | nowhere | **no `annual_surplus_deficit` metric** to bridge the two statements |
| 7 | component bounds: `cash_and_investments ≤ total_financial_assets`, `long_term_debt ≤ total_liabilities`, `tangible_capital_assets ≤ total_non_financial_assets` | would PASS | **nowhere** | plan §2 claims these; not implemented in `flags.py` |
| 8 | printed vs computed `net_debt` | testable | `flags.py` `cross_source_disagreement` via `crosscheck_value` | OK — this one is wired |

**Reasoning on the two real failures:**

- **Identity 4 (`expense_components`) is enforced but structurally cannot hold.** `flags.py`
  raises `sum_mismatch` when `labour + energy + materials ≠ operating_expenses` (2% tol). For any
  PSAB-basis statement, `operating_expenses` includes amortization that the three components do
  not, so the sum is short by the amortization amount (often 10–25% of opex) — **far** beyond 2%.
  Two bad outcomes: (a) honest, correctly-extracted data gets **false `sum_mismatch` flags**; or
  (b) to avoid the flag, the extractor is pushed to **stuff amortization/other into
  `materials_services_cost`**, corrupting the object breakdown. Either way the enforced identity is
  *wrong as written*. Fix: extend the identity to
  `labour + energy + materials + amortization + other_operating_expenses = operating_expenses`,
  which only works once those two metrics exist (Part D).

- **Identity 5 is presented as exact but is an approximation.** Subsidy equals the operating gap
  **only** when the annual surplus/deficit is zero. PSAB statements routinely show non-zero
  results (amortization of deferred capital contributions into revenue, gas-tax/carbon timing,
  one-time program funding). So enforcing `subsidy == expenses − revenue` at 2% will flag
  genuinely-correct statements whenever the annual result exceeds 2% of expenses. Adding
  `annual_surplus_deficit` lets the real identity be written:
  `operating_revenue + total_operating_subsidy + (other revenue) − operating_expenses = annual
  surplus/deficit`, with the residual explicit instead of forced to zero.

**`equations.py` vs `flags.py` cross-check (consumption consistency).** The solver
(`equations.py`) and the staging validator (`flags.py`) enforce **overlapping but different** sets:
identities 1, 2, 4, 5 are in `flags.py`; identities 1, 2, 3, 5 plus the ratio defs are in
`equations.py`. The **net-debt identity (3)** is cross-checked only by the solver, and the
**component-bounds (7)** are in neither — yet the balance-sheet plan §2 lists both as
`sum_mismatch` checks. This is a "claimed but not enforced" gap: either implement them in
`validate_cohort` or correct the plan. (Not a definition bug, but a rigor-promise the docs
overstate.)

**Bottom line for Part B.** The **balance sheet closes**; the **operating statement does not** —
it is missing the amortization and "other" expense lines (so its components can't sum) and the
annual surplus/deficit (so it can't connect to the balance sheet). The set today can show two
*partial* statements that **cannot be reconciled to each other**. Three additions
(`amortization`, `other_operating_expenses`, `annual_surplus_deficit`) make both statements
complete and every identity testable.

---

# Part D — New metrics that make the full picture clear

Ground rule held throughout: where an existing metric is deliberately **narrow** (operating), add
a deliberately **broad** companion (enterprise/total) measured the **same way for all**, so the
reader sees both the comparable core and the honest full scale — never one smuggled into the
other. And because the audience is **non-technical**, every addition must *earn* its slot: widely
reported, consistently definable, answers a real council question, not already derivable, and adds
**clarity** not clutter.

## D.1 The enterprise/total lens — `total_revenue` + `total_expenses` — **ADOPT**

- **Question.** "How big is this organization, all in?" Council asks "is Metrolinx a $0.3B fare
  business or a $0.8B+ enterprise?" — and the operating metrics, correctly, refuse to answer.
- **What becomes visible.** The true scale that `operating_revenue`/`operating_expenses`
  deliberately exclude: government transfers, capital-contribution amortization, the whole
  enterprise. It directly honours "a bigger, capital-heavy agency should look like one" **without**
  touching the operating numbers.
- **Standard anchor.** **PSAB Statement of Operations** totals — "total revenue" and "total
  expenses" exactly as audited. Same boundary for all (it's the audited bottom of each side).
- **Boundary drawable for all?** Yes — these are the literal statement totals; far *easier* and
  less judgment-laden than the operating split.
- **Ratio interactions.** None corrupting: keep these out of the operating ratios. Optionally
  enable one honest enterprise ratio later (e.g. `total_expenses / ridership` as "all-in cost per
  rider") clearly separated from the operating cost-per-rider.
- **Cost.** Low: two PSAB totals the extractor already lands on, two dictionary entries, one
  display block. Non-rankable (size).
- **Recommendation.** **Adopt.** This is the single highest-value addition — it satisfies the
  enterprise-scale requirement *and* anchors `annual_surplus_deficit` (D.3).

## D.2 `amortization` (depreciation) — own line — **ADOPT**

- **Question.** "How much is the agency consuming its capital each year, and what is the
  operating cost *without* that non-cash charge?"
- **What becomes visible.** (a) Makes `operating_expenses` **reconstructable on the CUTA/NTD
  operating basis** = `total operating expense − amortization`, resolving landmine A.6 without
  losing information; (b) reconciles the expense components (Part B identity 4); (c) surfaces
  capital intensity inside the operating statement.
- **Standard anchor.** CUTA/NTD treat amortization as the reconciling item between operating and
  PSAB-total expense; PSAB reports it as an expense object. Solidly anchored.
- **Boundary for all?** Yes — a single audited line in every PSAB statement.
- **Ratio interactions.** Lets farebox/cost-per-rider be computed on a **pinned** basis; if shown,
  the basis swing (A.6) becomes explicit rather than hidden.
- **Cost.** Low. Non-rankable (size); its *ratio* form is D.5.
- **Recommendation.** **Adopt.** Near-mandatory given A.6 and Part B.

## D.3 `annual_surplus_deficit` — the missing bridge — **ADOPT**

- **Question.** "Did the agency end the year up or down?" and, structurally, "do the two
  statements tie out?"
- **What becomes visible.** The **only** link from the operating statement to the balance sheet
  (Part B identity 6): `accumulated_surplus(end) = accumulated_surplus(start) +
  annual_surplus_deficit`. Also makes the subsidy identity (5) honest by giving the residual a
  home instead of forcing it to zero.
- **Standard anchor.** PSAB Statement of Operations bottom line. Self-validating via the
  roll-forward against `accumulated_surplus`.
- **Boundary for all?** Yes — one audited number per year.
- **Cost.** Low. Non-rankable (size/flow); but it powers a strong cross-statement cross-check.
- **Recommendation.** **Adopt.** The balance-sheet plan deferred it as a "Phase-2 nicety"; this
  review **upgrades it to recommended**, because without it neither statement reconciles.

## D.4 `passenger_fare_revenue` (fares-only) vs program-funded fares — **ADAPT / document now, add when sourceable**

- **Question.** "How much do *riders themselves* pay, versus fare revenue that is really subsidy
  (One Fare reimbursement, U-Pass, fare-capping programs)?"
- **What becomes visible.** Separates **earned** fare from **program-funded** fare. With One Fare
  live (2024+), this is a growing comparability leak: booked as fare by one agency and subsidy by
  another, it silently moves `operating_revenue`, `average_fare`, and `farebox_recovery_ratio`.
- **Standard anchor.** CUTA/NTD "fare revenue" is fares-only; provincial/third-party
  reimbursements belong in funding. So the *principle* is anchored; the *practice* is the hard
  part — agencies disclose the split inconsistently.
- **Boundary for all?** **At risk** — this is exactly where agencies diverge, so a clean
  cross-agency boundary is not yet drawable from disclosures.
- **Ratio interactions.** If adopted, `average_fare` could use the fares-only numerator (matching
  the standard, A.15), and farebox could be reported both ways.
- **Cost.** Medium (sourcing + reviewer judgment). Risk of clutter for a non-technical audience.
- **Recommendation.** **Document the boundary now** (add to `operating_revenue` Is-NOT: "fare
  revenue reimbursed by a third-party program is subsidy, not earned fare"); **add
  `passenger_fare_revenue` as an optional companion** only once it can be sourced consistently.
  Do not rank a fares-only metric until the boundary is reliable.

## D.5 Capital intensity made comparable — **ADOPT one, DEFER the rest**

`capital_expenditure`, `tangible_capital_assets`, and (proposed) `amortization` are all raw size
dollars. To make capital **comparable**, add a scale-free companion:
- **`asset_consumption_ratio` = accumulated amortization ÷ gross cost of TCA** — **ADOPT
  (preferred).** This is a recognized **PSAB/CICA state-of-good-repair indicator** ("how worn out
  is the capital stock?"), scale-free, and answers a real council question ("are we letting the
  system age?"). Shown as a value — **not rated** under the 2026-06-14 hero-box-only rule (it could
  be promoted to a rated hero later). Cost: needs gross TCA cost + accumulated amortization (the TCA
  note has both); one ratio. *Note:* it pairs naturally with `fleet_average_age` as the
  vehicle-specific version.
- **`capex_per_rider`** or **capex as a share of operating expense** — **DEFER.** Capex is lumpy
  (a single train order spikes one year), so a single-year ratio mis-signals; it needs multi-year
  smoothing the product doesn't do yet. Revisit when trends exist.

## D.6 `other_operating_expenses` (residual) — **ADOPT (paired with D.2)**

- **Question.** purely structural: "what closes the expense components to the total?"
- **What becomes visible.** Insurance/casualty, purchased transportation, taxes, misc — the
  CUTA/NTD "other" object class. Lets identity 4 actually balance and stops
  `materials_services_cost` from absorbing the residual (A.10).
- **Standard anchor.** CUTA/NTD object breakdown includes an "other" class.
- **Cost.** Low (it's a plug that the identity defines). Non-rankable; not displayed prominently —
  it exists to make the components honest.
- **Recommendation.** **Adopt** together with `amortization`; the two together make
  `expense_components` a real, enforceable identity.

## D.7 `net_debt_to_revenue` (PSAB sustainability ratio) — **OPTIONAL, consider replacing `debt_to_assets`**

Per A.21, the standards-anchored leverage/sustainability ratio is **net debt ÷ total annual
revenue** (a CICA/PSAB *Indicator of Financial Condition*), not the corporate `debt_to_assets`.
If `total_revenue` is adopted (D.1), this becomes cheap. **Recommendation:** add it as the
PSAB-anchored ranked leverage ratio and consider retiring `debt_to_assets` (or keep both, but
don't rank two near-collinear leverage ratios — that double-counts leverage in any composite).

## D.8 Verdict on the dual-lens, and how to present it without overwhelming

**Adopt the enterprise/total lens.** It is the correct, standards-anchored way to satisfy "a
bigger agency should look bigger" while keeping the operating metrics narrow and comparable —
the alternative (loosening `operating_revenue`/`operating_expenses`) destroys the product's whole
premise (shown in A.5/A.6).

**Presentation for a non-technical reader (the anti-clutter rule):** show **two clearly labelled
blocks, never one mixed number**, on the Financials tab:

- **"Operating — the comparable core"**: `operating_revenue`, `operating_expenses` (amortization
  excluded), `total_operating_subsidy`, the object components, and the four ratios (farebox,
  cost/rider, cost/hour, subsidy/rider). One plain caption: *"What it costs to run the service,
  measured the same way for every agency."*
- **"Enterprise — the full scale"**: `total_revenue`, `total_expenses`, `amortization`,
  `annual_surplus_deficit`, `capital_expenditure`. Caption: *"The whole organization, including
  capital and government funding — bigger here just means bigger, not better."* Non-rankable;
  shown as magnitudes with the agency's own statement as the source.

This way the comparable ranking lives entirely in the five rated hero metrics, the enterprise block
answers "how big" without ever polluting "how efficient," and the balance-sheet ratios are shown as
values (no longer ranked — 2026-06-14 decision).

**What NOT to add (earns no slot):** per-mode breakouts of every metric (display refinement, not
new metrics); a passenger-kilometre / load-factor family (rarely and inconsistently reported in
Canada); `reserves_reserve_funds` (display-only, no cross-check — the balance-sheet plan already
defers it, agreed); single-year `capex_per_rider` (D.5). Each would add cognitive load without
proportional clarity.

---

# Final prioritized recommendations

**Standards to anchor each metric to** (cite on every metric page):

| Family | Anchor |
|---|---|
| ridership | **NTD UPT** (unlinked boardings) |
| service supplied (hours, km) | **NTD VRH/VRM** = CUTA Revenue Vehicle Hours/Km |
| operating revenue/expense, subsidy, objects, efficiency ratios | **CUTA/NTD operating basis (amortization EXCLUDED)** |
| fleet size/age/accessible | NTD fleet conventions (per-mode where possible) |
| capital expenditure, TCA | CUTA capital / PSAB TCA |
| balance sheet (assets, liabilities, net debt, surplus) | **PSAB / PS 1201** net-debt model |
| net debt per capita, asset-consumption, net-debt-to-revenue | **CICA/PSAB Indicators of Financial Condition** |
| on_time_performance | none — agency-defined; **rated (hero box), flagged** — footnote or drop badge (pending) |
| fleet_capacity | **DROPPED** — replaced by a non-ranked 4-class fleet composition |

**Boundaries to pin (in priority order):**
1. **`operating_expenses` → amortization EXCLUDED (CUTA/NTD basis).** Add a structured
   `cost_basis` dimension (`operating`|`psab_total`); never rank across bases. *(landmine 2)*
2. **`operating_revenue` → earned operating revenue only;** exclude all government transfers,
   capital/construction recoveries, and third-party fare-program reimbursements; name these in
   Is-NOT. *(landmine 1)*
3. **Ranking — DECIDED:** rate only the five hero boxes (`ridership`, `operating_revenue`,
   `on_time_performance`, `cost_per_rider`, `subsidy_per_rider`); everything else is view-only
   (`comparable_flag=False`, driven off the hero set, not `NON_RANKABLE_METRICS`). This retires the
   two balance-sheet ranked ratios. **Open:** OTP keeps a "definitions vary" footnote or loses just
   its rank badge — record each agency's on-time window in a structured field either way.

**Metrics to ADD (in priority order):**
1. `amortization` — *(unblocks the operating basis + reconciles components)*
2. `annual_surplus_deficit` — *(the missing flow→stock bridge)*
3. `total_revenue`, `total_expenses` — *(the enterprise/total lens)*
4. `other_operating_expenses` — *(closes the component identity)*
5. `asset_consumption_ratio` — *(PSAB state-of-good-repair, scale-free; shown, not rated)*
6. *(optional)* `net_debt_to_revenue` — *(PSAB-anchored leverage; consider replacing
   `debt_to_assets`)*
7. *(when sourceable)* `passenger_fare_revenue` — *(earned vs program-funded fare)*

**Metrics to DOCUMENT / FIX:**
- Extend the enforced `expense_components` identity to include `amortization` +
  `other_operating_expenses` (today it is enforced but cannot hold — false flags / mis-bucketing).
- Make the subsidy identity honest with `annual_surplus_deficit` (today assumes a zero annual
  result).
- Implement (or strike from the plan) the **net-debt identity** and **component-bounds** checks in
  `validate_cohort` so `flags.py` matches the balance-sheet plan's promises.
- ✅ **Done (2026-06-14, commit `65ff697`):** regenerated `docs/reference/data-dictionary.md`
  (was stale at 31 metrics; now 32, incl. `fleet_capacity`). Re-run
  `python -m transitindex_ingest.dictionary` after any metric-set change.
- Add the One Fare / program-fare boundary note to `operating_revenue`.

**Metrics to REDESIGN or DROP:**
- `fleet_capacity` ("Fleet scale") — **DROPPED** (delete the metric + `MODE_CAPACITY_WEIGHT`).
  Replaced by a non-ranked 4-class fleet composition (Bus · Light rail · Heavy rail · Commuter
  rail) built from per-mode `fleet_size`, counted by trains for rail. See the build plan.
- `debt_to_assets` — keep (now view-only). If a balance-sheet leverage ratio is ever promoted to a
  rated hero, prefer the PSAB-anchored `net_debt_to_revenue`.

*This review changed no product code. The stale `data-dictionary.md` was regenerated and committed
separately (`65ff697`); the implementation of these decisions is specified in the build plan,
[metric-set-build-plan.md](metric-set-build-plan.md).*
