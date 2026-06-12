# PDF Extractor Improvement — Plan A (Phases 0–1, fully offline)

> **Status: APPROVED PLAN — not yet implemented.** Companion doc:
> [pdf-extractor-plan-b-api.md](pdf-extractor-plan-b-api.md) (Phases 2–4, API-gated).
> Execute Plan A completely (all gates green) before starting Plan B.
>
> **Hard rule: this plan makes ZERO Anthropic API calls.** Every change is verified by
> the offline pytest suite (`cd ingest && python -m pytest`) plus replay against the
> recorded smoke data. If a step seems to need an API call, stop — it belongs in Plan B.

## Why (context for the implementing session)

The default extractor `ingest/transitindex_ingest/pdf/chunked_hybrid.py`
(`ChunkedHybridExtractor`) was smoke-tested 2026-06-12 on 10 catalog PDFs: all
succeeded, 438 merged values, ~$0.50/PDF — but **38% of values (169/438) came out at
confidence ≤ 0.5**, i.e. flagged for human review. The review burden, not cost, is the
bottleneck. Evidence: `ingest/_smoke10_result.json` (per-PDF merged values with
notes/quotes/confidence; currently untracked).

Root causes this plan fixes offline:

1. **Merge false-conflicts** — `merge_values` compares values with exact equality, so a
   rounded-summary reading vs an exact-statement reading of the *same* figure (TTC
   12,060,661,000 vs 12,059,032,000 — 0.014% apart) is flagged as a conflict.
2. **`unit` free-text chaos** — 27 variants ('CAD', '$000s', 'thousands of dollars'…).
   The numeric values are already correctly scaled to absolute units; only the label is
   noise, and it trips `unit_mismatch` validation. The canonical unit is derivable from
   `refdata.METRICS`.
3. **Garbage slips through** — ttc 2024 `total_assets=39` (conf 0.3); `source_quote`
   exists but is optional and never checked against the value.
4. **Pure waste** — `cache_control` on per-chunk content (sent once, never re-read) pays
   the 1.25× cache-write premium for nothing, ~15–20% of input cost.
5. **Provenance mislabeled** — non-contiguous image batches (pages 1,2,4,13,14) are
   captioned "pages 1–14".
6. **Context loss** — the chunker can separate an "(in thousands of dollars)" header
   from its table rows, and chunks carry no section heading.

## Ground rules (from CLAUDE.md — binding)

- Surgical diffs only. Touch nothing not listed here. Match existing style.
- The `Extractor` seam (`pdf/extractor.py`) is **frozen** in Plan A: no signature or
  dataclass changes there, and **no new fields on `ExtractedValue`**.
- Do not modify: `pdf/router.py`, `pdf/docstrange_path.py`, `pdf/claude_pdf.py`,
  `pdf/ensemble.py` (except where step A4 notes a test update), `equations.py`,
  anything in `db/`, `web/`, or migrations.
- Every step ends with its verify gate green before the next step starts.
- All thresholds become named module constants (the codebase style), never inline magic
  numbers.

---

## Phase 0 — measurement first (recording + gold candidates)

### Step 0.1 — Commit the smoke evidence as a fixture

Copy `ingest/_smoke10_result.json` → `ingest/tests/fixtures/smoke/smoke10_2026-06-12.json`
(create the directory). This is the frozen "before" baseline that Phase 1's replay and
Phase 2's comparison read. Do not edit its contents.

**Verify:** file exists, `json.load` succeeds, contains 10 entries with keys
`doc_id, slug, year, doc_type, values, conflicts, lowconf`.

### Step 0.2 — Per-segment raw recording in the extractor

Today `ChunkedHybridExtractor.extract` (chunked_hybrid.py:244) throws away which
segment produced which values. Add recording so merge logic can be replayed offline on
future runs.

1. In `pdf/llm.py`, next to `ExtractedValue`, add two pure serializers:

   ```python
   def value_to_dict(v: ExtractedValue) -> dict: ...
   def value_from_dict(d: dict) -> ExtractedValue: ...
   ```

   `Decimal` fields (`value`, `confidence`) serialize via `str(...)` and parse back via
   `Decimal(...)`. All other fields pass through. Round-trip must be lossless.

2. In `ChunkedHybridExtractor.extract`, build
   `segments_raw = [{"label": <segment label>, "values": [value_to_dict(v), ...],
   "input_tokens": <int>, "error": <str or None>}, ...]` (one entry per segment, in
   segment order) and add it to the returned `diagnostics` dict. Always on — no flag.

**Verify:** new tests in `ingest/tests/test_chunked_hybrid.py`:
- round-trip `value_to_dict`/`value_from_dict` on a value with every optional field set;
- driving the extractor with the existing scripted fake client yields
  `diagnostics["segments_raw"]` whose per-label values match what the fake returned.

### Step 0.3 — Gold-candidate derivation (human-confirmed gold fixtures)

One synthetic gold fixture exists (`ingest/tests/fixtures/gold/ttc_annual_2024.json` —
see its format; `eval/gold.py:load_gold` reads it). Derive **candidate** gold fixtures
from the smoke data for the user to confirm by hand.

New module `ingest/transitindex_ingest/eval/candidates.py`:

```python
def derive_candidates(smoke_json: Path, doc_id: int, out_dir: Path) -> Path: ...
```

plus an `argparse` `main()` so it runs as
`python -m transitindex_ingest.eval.candidates ingest/tests/fixtures/smoke/smoke10_2026-06-12.json --doc 59 --out ingest/tests/fixtures/gold/candidates/`.

Rules:
- Use only values with `period_kind == "annual"` and `year ==` the doc's own `year`.
- One record per metric: keep the highest-confidence reading.
- Record format mirrors the existing gold fixture exactly
  (`metric_code, true_value, unit, tolerance, should_flag`) with
  `unit` = the canonical `refdata.METRICS[code]["unit"]` (NOT the smoke free-text),
  `tolerance` = `"0.005"`, `should_flag` = `false`. Add one extra key per record,
  `"evidence": {"page", "conf", "quote", "note"}`, so the human can confirm without
  reopening the PDF (`load_gold` ignores extra keys — verified).
- Top level: `agency_slug`, `period_year`, `period_kind: "annual"`, and a `description`
  that says **CANDIDATE — UNCONFIRMED, do not use in eval until moved to gold/**.

Generate candidates for three docs from the smoke file: doc_id **59** (ttc 2019
annual_report), the **edmonton-ets 2019 financial_statement** entry (the 82%-review
worst case — find its doc_id in the JSON), and one **[C] city doc** (calgary or
burlington entry — whichever is present).

**Human gate (the project owner, not the model):** the user reviews each candidate file,
fixes/deletes wrong rows, sets `should_flag: true` on genuinely ambiguous figures, and
moves confirmed files from `gold/candidates/` to `gold/` (renamed
`<slug>_annual_<year>.json`). Implementation continues to Phase 1 without waiting, but
Plan B's scoring needs at least 2 confirmed files.

**Verify:** unit test drives `derive_candidates` against the committed smoke fixture and
asserts: only doc-year annual rows, one row per metric, canonical units, candidate
marker present.

---

## Phase 1 — the offline fixes

Recommended order: 1.1 (trivial deletions) → 1.2 → 1.3 → 1.4 → 1.5 → 1.6 → 1.7 (replay
report last, since it exercises everything).

### Step 1.1 — Delete dead cache_control; fix image-batch page labels

File: `pdf/chunked_hybrid.py`.

a) In `_segments`, remove `"cache_control": {"type": "ephemeral"}` from the per-chunk
   text block (~line 311) and from the image `document` block (~line 325). **Keep** the
   system-prompt `cache_control` in `_segment_values` (line 184) — that one is correct.

b) Add a helper and use it for both the segment label and the prompt caption:

   ```python
   def _page_label(pages: list[int]) -> str:
       """Compact human label for a 1-based page list: [1,2,4,13,14] -> '1-2, 4, 13-14'."""
   ```

   Replace the `f"img{pages[0]}-{pages[-1]}"` label with `f"img{_page_label(pages)}"`
   and the caption `f"Scanned report pages {pages[0]}–{pages[-1]}"` with
   `f"Scanned report pages {_page_label(pages)}"`.

**Verify:** tests — `_page_label([1,2,4,13,14]) == "1-2, 4, 13-14"`, single page,
fully contiguous; grep confirms exactly one `cache_control` remains in the module
(the system prompt one); existing extractor tests still pass.

### Step 1.2 — Merge tolerance (kill false conflicts)

File: `pdf/chunked_hybrid.py`, `merge_values` (lines 140–174).

New constant: `MERGE_REL_TOLERANCE = Decimal("0.005")  # readings within 0.5% are the same figure`.

New behavior for a group with >1 distinct values:
- `spread = (max_v - min_v) / max(abs(max_v), abs(min_v))` over the group's values
  (guard: if both max and min are 0 they're equal already; if `max(abs(...)) == 0`
  treat as agreeing).
- `spread <= MERGE_REL_TOLERANCE` → **agree**: keep the *most precise* reading — the
  value whose integer string has the **fewest trailing zeros** (a rounded summary like
  12,060,000,000 loses to an exact 12,059,032,000); tie → highest confidence. The kept
  value gets `confidence = max(confidences in the group)` (corroborated readings) and a
  note appended via `_with_note`: `f"✓ {len(vs)} readings agree within 0.5%"`.
- `spread > MERGE_REL_TOLERANCE` → existing conflict path **unchanged** (real
  restatements exist — TTC capex readings 1.2% apart must STILL flag).

**Verify:** new tests in `test_chunked_hybrid.py`:
- 12060661000 vs 12059032000 (0.014% apart) → merged, no "disagree" note, confidence =
  max of the two;
- values 1.2% apart → still conflict-flagged at ≤ 0.5 confidence;
- 525500000 vs 530000000 (0.86% apart) → still conflicts (this is a real scope
  difference, resolved in Plan B, not here);
- trailing-zero precision rule picks the exact reading over the rounded one.
- Existing merge tests (`test_merge_*`) must still pass unmodified — values exactly
  equal and values wildly different behave as before.

### Step 1.3 — Canonical unit from the metric dictionary

File: `pdf/llm.py`, `_row_to_value` (lines 229–252). `METRICS` is already imported
(line 21).

Change `unit=row["unit"]` to `unit=METRICS[row["metric_code"]]["unit"]`. The model's
free-text unit is discarded (the numeric value is already absolute via
`printed_scale`; the free text survives in `segments_raw` recordings and in
`source_quote`). `metric_code` is schema-constrained to `SOURCED_METRIC_CODES`, so the
lookup cannot KeyError.

Effects to be aware of (and assert):
- `validation/flags.py:unit_mismatch` heuristic #1 (`record.unit != meta["unit"]`) can
  no longer fire for LLM-extracted values — that whole flag-noise class dies.
- `pipeline._to_record` line 97 (`currency="CAD" if ev.unit == "CAD"`) now behaves
  consistently for all currency metrics.

**Verify:** update any test in `test_claude_extractor.py` / `test_number_parsing.py` /
`test_markitdown_path.py` / `test_chunked_hybrid.py` that asserted free-text unit
passthrough from a tool row; add one test: a row with `unit: "thousands of dollars"`
for `operating_expenses` yields `unit == "CAD"`. Tests that construct `ExtractedValue`
directly (FakeLLMClient/FakeExtractor paths) are untouched by design.

### Step 1.4 — Require source_quote and check the digits

File: `pdf/llm.py`.

a) New pure function near `parse_number`:

   ```python
   def quote_supports_value(printed: str, quote: Optional[str]) -> Optional[str]:
       """None when the quote contains the printed value; 'missing' when there is no
       quote; 'mismatch' when there is one but the digits aren't in it."""
   ```

   Normalization: strip spaces / non-breaking spaces / narrow nbsp / commas and
   accounting parentheses from both strings; the check is `printed_norm in quote_norm`,
   also trying the comma-decimal variant of `printed` (`"525.5"` matches `"525,5"`).
   Compare on the **as-printed** string (`row["value"]`), never the scaled Decimal.

b) In `_row_to_value`, apply the result with two new constants:

   ```python
   QUOTE_MISSING_CONFIDENCE_CAP = Decimal("0.5")
   QUOTE_MISMATCH_CONFIDENCE_CAP = Decimal("0.3")
   ```

   `'missing'` → `confidence = min(confidence, 0.5)`, note appended `"no source quote"`.
   `'mismatch'` → `confidence = min(confidence, 0.3)`, note appended
   `"⚠ value not found in its source quote"`. Never drop the value here.

c) Contract tightening (offline text edits; their effect is measured in Plan B's run):
   add `"source_quote"` to `EXTRACTION_TOOL`'s `required` list (line 155-163) and add
   one rule line to `EXTRACTION_SYSTEM_PROMPT`: *"source_quote is REQUIRED: the verbatim
   on-page text you read the number from, containing the digits as printed."*

**Verify:** unit tests for `quote_supports_value` (exact match, comma-thousands quote,
French comma-decimal, missing quote, wrong digits); `_row_to_value` caps confidence and
appends notes as specced; existing `_row_to_value` tests updated to include quotes where
they now matter.

### Step 1.5 — Confidence floor + currency magnitude sanity

a) File: `pdf/chunked_hybrid.py`. New constant
   `CONFIDENCE_FLOOR = Decimal("0.3")  # below this a reading is noise, not data`.
   In `extract`, **before** `merge_values`, partition `all_values`: values with
   `confidence < CONFIDENCE_FLOOR` are dropped and counted in
   `diagnostics["dropped_below_floor"]` (int). Dropping pre-merge stops garbage from
   poisoning a good reading into a false conflict. (Boundary: exactly 0.3 survives —
   so step 1.4's mismatch-capped values stay visible to reviewers.)

b) File: `validation/flags.py`, `unit_mismatch` (lines 81–104). Add heuristic #3 with
   constant `_CURRENCY_FLOOR = Decimal("10000")`: a `unit_type == "currency"` metric
   with `record.value != 0` and `abs(value) < 10000` is implausible for agency-level
   finances (the smoke garbage `total_assets=39`) → return `UNIT_MISMATCH`. Update the
   docstring's heuristic list.

**Verify:** tests — extractor drops a 0.2-confidence value and reports the count; a
0.3 value survives; `unit_mismatch` flags `total_assets=39 CAD`, passes
`total_assets=39000000`, passes `fleet_size=39` (count, not currency), passes a 0
currency value.

### Step 1.6 — Inject section heading + scale declaration into chunk context

File: `pdf/chunked_hybrid.py`.

New function (refactor `chunk_markdown`'s packing loop into it; `chunk_markdown` keeps
its exact signature/behavior by delegating and dropping the context):

```python
_SCALE_RE = re.compile(r"\((?:in\s+|en\s+)?(?:\$?\s*000s?|thousands|milliers|millions)[^)]*\)", re.IGNORECASE)
_HEADING_RE = re.compile(r"^#{1,6}\s+\S")

def chunk_markdown_with_context(md: str, *, target_lines: int = DEFAULT_TARGET_LINES) -> list[tuple[str, str]]:
    """Like chunk_markdown, but each chunk comes with a context header: the most
    recent markdown heading and the most recent scale declaration ('(in thousands
    of dollars)') seen in the document BEFORE the chunk's first line. Empty string
    when neither has occurred yet."""
```

Track `last_heading` / `last_scale` line-by-line while reading blocks; the context for a
chunk is the state at its first block. Context string format (omit missing parts, empty
if both missing):
`Context from earlier in the document — section: "<heading>"; scale declaration: "<match>"`.

In `_segments`, switch to `chunk_markdown_with_context` and, when context is non-empty,
append it as a third line of the **intro** text block (the `Agency: ...` block), never
inside the chunk text itself.

**Verify:** tests — a scale declaration in chunk 1 appears in chunk 2's context; a later
declaration supersedes an earlier one; headings tracked independently of scale; no
heading/scale → empty context and an intro block identical to today's;
`chunk_markdown`'s existing four tests pass byte-identical.

### Step 1.7 — Offline replay report against the smoke fixture

New module `ingest/transitindex_ingest/eval/replay.py` with a `main()`
(`python -m transitindex_ingest.eval.replay [path-to-smoke-fixture]`, default the
committed fixture). For each doc entry it reports, using ONLY the recorded JSON:

1. **Conflicts that collapse:** parse every value note matching
   `⚠ chunks disagree — <v1>, <v2>[, ...] (reviewer confirm)` into its candidate list;
   apply step 1.2's spread rule; count collapsed vs surviving.
2. **Quote check on real data:** run step 1.4's `quote_supports_value` over each
   recorded (value, quote) pair — note: recorded values are post-scaling, so derive the
   printed string check leniently (digits of the value with trailing zeros stripped
   must appear in the quote's normalized digits); report match/missing/mismatch counts.
   This is a *report*, not a gate — it sizes the problem.
3. **Summary table** per doc + totals: values, conf≤0.5 before, estimated conf≤0.5
   after (collapsed conflicts and unit-label noise removed), conflicts before/after.

Print the table and write `ingest/_replay_report.json` (untracked, like the smoke file).

**Verify:** pytest test pins the headline numbers for doc 59 (ttc 2019): it has 13
recorded conflicts; assert the TTC 12,060,661,000/12,059,032,000-style pair collapses
and the 525.5M/530M pair survives (extract the exact note strings from the fixture in
the test). The final replay run's totals get pasted into the PR description as the
Phase 1 "expected improvement" baseline.

---

## Acceptance criteria (Plan A done)

1. `cd ingest && python -m pytest` — full suite green with **no** `ANTHROPIC_API_KEY`
   set and no network.
2. All new tests listed above exist and pass.
3. `git diff` touches only: `pdf/chunked_hybrid.py`, `pdf/llm.py`,
   `validation/flags.py`, `eval/candidates.py` (new), `eval/replay.py` (new),
   `ingest/tests/...` (tests + fixtures), and the smoke fixture copy. Anything else is
   scope creep — revert it.
4. Replay report shows a conflict-collapse count > 0 and is attached to the PR.
5. Candidate gold files exist for 3 docs and are awaiting user confirmation.
6. Exactly one `cache_control` left in chunked_hybrid.py.
7. `docs/STATUS.md` row for this doc updated to reflect reality at session end.
