# PDF Extractor Improvement — Plan B (Phases 2–4, API-gated)

> **Status: APPROVED PLAN — not yet implemented.** Prerequisite:
> [pdf-extractor-plan-a-offline.md](pdf-extractor-plan-a-offline.md) fully landed
> (all acceptance criteria green) AND the user has confirmed at least 2 gold fixtures
> (moved from `gold/candidates/` to `gold/`).
>
> **Hard rule: every Anthropic API spend in this plan requires an explicit go-ahead
> from the user first** — name the doc ids and the estimated cost, then wait. All code
> in this plan is still written and tested OFFLINE (fake clients, recorded fixtures);
> the API runs only *measure* it. Supabase Storage downloads are allowed (not API spend).

## Why

Plan A removes the mechanical review noise. Plan B removes the *semantic* noise the
2026-06-12 smoke test exposed, then cuts cost:

- **Scope collisions** — TTC subway 204M / bus 181M / streetcar 35M vs total 420M, and
  TransLink journeys 272M vs boardings 453M, collide under one merge key because no
  scope/definition dimension exists.
- **Forecasts as data** — miway 2020 business_plan emitted 2022–2029 projections;
  edmonton service_plan similar. No actual/budget/forecast distinction.
- **[C] city docs unsegmented** — Calgary accumulated_surplus $21B / Burlington $1.06B
  are whole-city figures tagged to the transit agency. The catalog row knows
  `doc_type` + `author_label` ('T' transit-own / 'C' city) + `year`; the extractor only
  receives `agency_slug`.
- **Cost** — ~$0.50/PDF at smoke. Targets: review rate 38% → **<10%**, cost →
  **$0.10–0.15/PDF**, recall same-or-better vs gold.

Non-goals (do NOT build): dual-model everywhere, Fable 5 usage, fine-tuning/local
models, DocStrange.

## Ground rules

- The `Extractor` Protocol stays drop-in compatible: `ExtractionRequest` /
  `ExtractedValue` gain **optional fields with defaults only**; every existing caller
  and test keeps working unchanged.
- Offline tests for everything; the suite runs with no API key.
- Surgical diffs; thresholds as named constants; match existing style.
- Do not modify: `pdf/router.py`, `pdf/docstrange_path.py`, `equations.py` solver
  semantics, db migrations (none are needed for Phases 2–3).

---

## Phase 2 — scope, basis, and document context (one paid eval run at the end)

### Step 2.1 — `service_scope` + `basis` on the extraction contract

File: `pdf/llm.py`.

a) `ExtractedValue` gains two defaulted fields:

   ```python
   service_scope: str = "total"   # 'total'|'conventional'|'specialized'|'system_wide'|'mode_subset'|'city_wide'
   basis: str = "actual"          # 'actual'|'budget'|'forecast'|'restated'
   ```

b) `EXTRACTION_TOOL` item properties gain (NOT added to `required`; `_row_to_value`
   defaults them):

   - `service_scope`: enum `["total","conventional","specialized","system_wide","mode_subset","city_wide"]`
     — description: "'total' = whole agency. 'conventional'/'specialized' (paratransit)/
     'system_wide' as labeled by the source. 'mode_subset' = one mode only (bus-only,
     subway-only). 'city_wide' = a whole-city figure (city consolidated statements),
     not the transit service."
   - `basis`: enum `["actual","budget","forecast","restated"]` — description:
     "'actual' = reported result; 'budget'/'forecast' = planned or projected figures
     (multi-year plans, budget columns); 'restated' = a prior-year figure restated."

c) `_row_to_value` parses both with defaults; `basis == "restated"` appends
   `"restated figure"` to the note. `value_to_dict` / `value_from_dict` (Plan A
   step 0.2) carry both fields.

d) System-prompt rules (append to `EXTRACTION_SYSTEM_PROMPT`): one line each for scope
   and basis mirroring the descriptions above, plus: *"A 'planned', 'projected',
   'budget' or future-year figure is NEVER basis='actual'."*

e) The first four `service_scope` values intentionally mirror
   `contract.ServiceScope` (`contract.py:24`); `mode_subset` / `city_wide` exist only
   inside extraction and are filtered out before staging (step 2.3).

**Verify:** `_row_to_value` defaults and parses both fields; serializer round-trips
them; schema enums exactly as above.

### Step 2.2 — Merge key includes scope + basis

File: `pdf/ensemble.py`, `_key` (line 35) — extend the tuple:

```python
return (v.metric_code, v.period_kind, v.period_year, v.period_month, v.service_scope, v.basis)
```

`chunked_hybrid.merge_values` imports `_key`, so the TTC mode split and TransLink
journeys-vs-boardings stop colliding with the totals automatically.

**Verify:** merge test — same metric/period with scopes `total` vs `mode_subset` →
two values, no conflict; `actual` vs `forecast` → two values, no conflict.

### Step 2.3 — Out-of-scope filtering after merge

File: `pdf/chunked_hybrid.py`, in `extract` after `merge_values`:

- drop `service_scope in {"mode_subset", "city_wide"}` →
  `diagnostics["dropped_scope"]` (int);
- drop `basis in {"budget", "forecast"}` → `diagnostics["dropped_basis"]` (int);
- keep `restated` (it is an actual, just restated — the note from 2.1c marks it).

Rationale: the metric set wants agency-level actuals; everything else is junk for the
staging queue (per the standing "extractor locked to the metric set" rule) but stays
countable in diagnostics. The opt-in experimental extractors do not get this filter.

File: `pdf/pipeline.py`, `_to_record` (line 93): `service_scope=ev.service_scope`
replaces the hardcoded `"total"`. Only contract-valid scopes can reach here (the filter
above removed the other two; legacy/Fake paths default to `"total"`).

**Verify:** extractor test — a fake client returning a forecast row and a city_wide row
yields neither in `values`, both counted; pipeline test — an `ExtractedValue` with
`service_scope="conventional"` stages a `pending_values` row with that scope (existing
FakeExtractor path, offline).

### Step 2.4 — Pass the catalog row's document context to the extractor

a) `pdf/extractor.py`, `ExtractionRequest` gains three optional fields (frozen
   dataclass, defaults `None` — seam-compatible):

   ```python
   doc_type: Optional[str] = None      # catalog doc_type ('annual_report', 'budget', ...)
   author_label: Optional[str] = None  # 'T' transit-own / 'C' city
   doc_year: Optional[int] = None      # the catalog row's report year
   ```

b) `pdf/pipeline.py`, `run_pdf` gains keyword-only params
   `doc_type=None, author_label=None, doc_year=None`, forwarded into the
   `ExtractionRequest` it builds (line 140).

c) `scan.py`, `scan_document`: pass `doc.doc_type`, `doc.author_label`, `doc.year` into
   `run_pdf`.

d) `cli.py` `pdf` and `pdf-smoke` commands: optional `--doc-type`, `--author`,
   `--year` args passed through (default None; reuse the existing `_DOC_TYPES` choices
   where applicable).

**Verify:** scan test (existing `test_scan.py` fakes) asserts the request the fake
extractor receives carries the doc row's three fields; an `ExtractionRequest()` built
the old way still works everywhere.

### Step 2.5 — Document-aware prompt + per-metric definition canon

File: `pdf/chunked_hybrid.py`.

a) **Definition canon:** in `__init__`, lazily import
   `..dictionary.extraction_guidance` and build
   `self._system_prompt = EXTRACTION_SYSTEM_PROMPT + "\n\nMetric definitions (the canon — map printed figures onto these, nothing else):\n" + extraction_guidance()`.
   `_segment_values` gains a `system: str` parameter and uses it instead of the global.
   (`extraction_guidance` already exists at `dictionary.py:262` and emits IS/IS-NOT,
   EN+FR labels, and confusions per sourced metric — it was built for this and is
   currently unused by the prompt. It is cached by the system-prompt `cache_control`,
   so the extra length is paid once per run, not per segment.)

b) **Per-document intro lines** in `_segments`, appended to the existing
   `Agency: {agency}` intro block, derived from the request's new fields (skip any line
   whose source field is None):

   - `Document: {doc_type} for {doc_year}, published by ` +
     (`"the transit agency itself."` if `author_label == "T"` else
     `"the CITY government (consolidated city-wide financial statements)."`)
   - if `author_label == "C"`: `City-published document: balance-sheet and financial
     figures that cover the WHOLE CITY are service_scope='city_wide' — only figures
     explicitly broken out for the transit service/segment may use other scopes. If the
     statements have no transit segment breakout, emit NO city-wide financials.`
   - if `doc_type` in `{"budget", "business_plan", "service_plan"}`: `This is a
     plan/budget document: figures for {doc_year} and later are basis='budget' or
     'forecast' unless explicitly reported as actual results; prior-year actuals are
     basis='actual'.`

**Verify:** offline test with the scripted fake client captures the request content and
asserts the intro lines for a `C`/`budget` request and their absence for a bare
request; system prompt contains a known dictionary phrase (e.g. "unlinked").

### Step 2.6 — The eval/smoke runner (replaces the ad-hoc smoke script)

New module `ingest/transitindex_ingest/eval/smoke.py` with `main()`
(`python -m transitindex_ingest.eval.smoke --docs 59,64,53,31,13,19,25,44,1,7 --out <path>`):

- For each doc id: load the catalog row (repo), download from Supabase Storage
  (`storage.py`), run `ChunkedHybridExtractor` directly (NOT run_pdf — no staging
  side-effects), passing doc_type/author_label/doc_year.
- Write a result JSON in the same shape as the smoke fixture **plus**
  `diagnostics["segments_raw"]`, `dropped_scope/basis/below_floor`, and timing/cost.
- Compute per-doc and total: values, review rate (`conf ≤ 0.5` share), conflicts,
  dropped counts, est cost.
- `--baseline <path>` prints a before/after delta table against the committed
  2026-06-12 fixture.
- `--gold <dir>` scores any doc whose `(slug, year)` has a confirmed fixture in
  `ingest/tests/fixtures/gold/` via `eval/gold.py:run_eval` (map merged values →
  `ExtractedAssessment`: filter to the gold year/kind + scope `total`/basis `actual`;
  flags = `("low_confidence",)` when conf < 0.7 else `()`).

**Verify (offline):** test drives `main`'s internals with a `FakeExtractor` and a fake
storage/repo; baseline-delta math unit-tested.

### Step 2.7 — THE RUN (paid — **ask the user first**)

Quote to the user: same 10 doc ids `59,64,53,31,13,19,25,44,1,7`, est. **$3–5 total**
(cache-write removal should put it under the smoke's $5.04). On approval, run step
2.6's command, commit the report (not the raw PDFs), and evaluate the gates:

| Gate | Threshold |
|---|---|
| Review rate (conf ≤ 0.5) | **< 15%** to proceed (< 10% is the target) |
| Gold precision (confirmed fixtures) | ≥ baseline run's values for those docs |
| Recall (distinct true metrics found/doc) | ≥ baseline − 1 |
| Forecast leakage (plan/budget docs) | 0 future-year `basis='actual'` values |
| City leakage ([C] docs) | 0 whole-city figures staged as transit |
| Cost/PDF | ≤ $0.40 (Phase 3 does the big cut) |

Any gate red → fix offline, re-ask, re-run (one re-run budgeted). All green → Phase 3.

---

## Phase 3 — cost (after Phase 2 verified)

### Step 3.1 — Deterministic chunk prefilter (tuned offline, free)

a) Pure function in `pdf/chunked_hybrid.py`:

   ```python
   def chunk_is_relevant(chunk: str, keywords: frozenset[str]) -> bool
   ```

   Keep a chunk when (any keyword appears, case-insensitive) OR (numeric density: ≥ 3
   lines containing ≥ 2 number tokens — a table). Keywords built once from
   `dictionary.load_dictionary()`: every `labels_en` + `labels_fr` + display name,
   lowercased, plus `"$"`.

b) Tuning script `eval/prefilter_tune.py`: for all 64 catalog PDFs, download
   (storage — free), run markitdown locally (free), chunk, and report kept-chunk %
   overall. **Safety gate:** for every doc with a confirmed gold fixture, every chunk
   containing a gold record's `source_quote` digits must be kept — if not, loosen the
   rule, never ship a filter that drops a gold quote.

c) Wire as `prefilter: bool = True` kwarg on `ChunkedHybridExtractor`;
   `diagnostics["chunks_skipped"]` counts drops. Image batches are never prefiltered.

**Verify:** offline tests (obvious keep/drop chunks); tuning report committed to the PR;
expected effect ~30–50% fewer text segments.

### Step 3.2 — Batch API path for backlog scans (−50%)

New module `pdf/batch_scan.py` (lazy anthropic import):

- `batch_scan(repo, storage, doc_ids, *, api_key, model=...) -> dict` — for each doc,
  build segments via a `ChunkedHybridExtractor`'s `_segments` (reuse, don't copy);
  submit ALL segments of all docs as one `client.messages.batches.create` call with
  `custom_id = f"{doc_id}:{label}"`; poll `batches.retrieve` until `ended` (sleep
  loop with a max-wait); parse each result through the same tool-use path as
  `_segment_values`; group by doc; apply the same floor → merge → scope/basis filter;
  stage per doc through `run_pdf` with a `FakeExtractor` carrying the merged values
  (reuses the unchanged pipeline + validators); mark catalog rows scanned/failed like
  `scan.py` does.
- CLI: `docs-scan --batch <ids…>` flag (cli.py) routing to it. **Paid — same ask-first
  rule.** Use for the ~54-PDF backlog, where the −50% batch discount matters most.

**Verify (offline):** fake batch client scripted through create/retrieve/results;
asserts custom_id round-trip, per-doc merge isolation, and failure of one doc not
sinking the batch.

### Step 3.3 — Sonnet for text segments (gated on gold parity)

`ChunkedHybridExtractor` gains `text_model: Optional[str] = None`: when set, md
segments call `text_model`, image batches keep `self._model` (Opus — scans stay on the
strong model). Plumb the per-segment model through `_segment_values`; cost estimate in
diagnostics uses the right rate per segment (`_INPUT_USD_PER_MTOK`).

**Gate (paid, ask first):** run the 2.6 runner on the gold-fixture docs with
`text_model="claude-sonnet-4-6"`; adopt as the scan/CLI default only if gold precision
and recall match the Opus text baseline and review rate is not worse. Combined Phase 3
arithmetic when all three land: ~$0.50 → **~$0.10–0.15/PDF**
(no cache premium − prefiltered chunks − Sonnet text at 3/5 the input rate − batch −50%
for backlog).

---

## Phase 4 — auto-corroboration (sketch — confirm design with the user before building)

### 4.1 Equation-identity corroboration (post-merge, in-document)

After merge+filter in `chunked_hybrid.extract`: group values by
`(period_year, service_scope='total', basis='actual')`; where the PSAB identities
(`validation/flags.py:sum_mismatch`'s two identities — components→expenses,
subsidy=expenses−revenue) hold within 0.5%, raise every participating value to
`confidence = max(conf, 0.85)` with note `"✓ identity check passed"`. Identities
failing → leave confidence alone (validation already flags the cohort). Effect:
internally-consistent financial statements exit the review queue wholesale.

### 4.2 Cross-document corroboration + precedence at promotion

In `promotion.py`: when two *different documents* yield the same
(agency, metric, period, scope) within 0.5%, auto-corroborate (note + confidence
bump); on conflict, precedence **[C] beats [T] for balance-sheet/financial metrics,
[T] beats [C] for operations** (ridership, service hours/km, fleet). **Open design
issue:** pending rows don't carry `author_label` — it must be joined via the source
document ↔ catalog linkage (`scan.py`'s deferred `source_document_id` note), which may
need a small migration. Do NOT implement until that linkage design is confirmed with
the user.

---

## Acceptance criteria (Plan B done through Phase 3)

1. Offline suite green with no API key; all new offline tests in place.
2. Phase 2 run gates met (table in 2.7), report committed.
3. Forecast/city leakage = 0 on the plan/budget and [C] docs in the run.
4. Phase 3: tuning report committed; batch path exercised on at least one real backlog
   batch (user-approved spend); Sonnet adopted only on proven gold parity.
5. Review rate < 10% and cost ≤ $0.15/PDF on the final measured run — or a written
   note in this doc's header explaining the gap and what remains.
6. `docs/STATUS.md` updated; Phase 4 remains `sketch` until separately approved.
