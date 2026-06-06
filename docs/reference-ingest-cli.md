# Reference: the ingestion CLI (`transitindex_ingest`)

Every command the Python ingestion pipeline exposes, with its arguments, defaults,
and requirements. This is the complete factual listing. For a friendly, no-coding
walkthrough of the everyday tasks, see [managing-data.md](managing-data.md).

All commands run from the `ingest/` folder and share one prefix:

```
python -m transitindex_ingest <command> [options]
```

**Where the data goes.** Each command chooses its database from `DATABASE_URL`
(in the project-root `.env`):

- `DATABASE_URL` **set** → writes to that Postgres database.
- `DATABASE_URL` **unset** → runs against an in-memory database and saves nothing
  (a dry run). The command still runs and prints results, but a `[note]` line
  warns that nothing was persisted.

A few commands need extra settings; they are called out per command and collected
under [Environment](#environment) at the end.

---

## Data loaders

Fast, diff-aware bulk loads of open-data sources. Re-running supersedes only the
rows that changed (identical rows are skipped, so no duplicates accumulate). Each
writes a JSON result summary and exits `0` on success, `1` if a self-check fails.
The design is described in [statcan-loader-design.md](../statcan-loader-design.md).

### `statcan-load` (alias: `statcan`)

Load the StatCan monthly table 23-10-0307 (monthly ridership + operating revenue,
about a dozen agencies).

```
python -m transitindex_ingest statcan-load <csv> [--reset] [--result PATH]
```

| Argument | Type | Default | Meaning |
|---|---|---|---|
| `csv` | path (required) | — | The 23-10-0307 CSV export (UTF-8; a leading BOM is tolerated). |
| `--reset` | flag | off | Delete all existing StatCan-agency data first, then reload (forced full reload). |
| `--result` | path | `load_statcan_result.json` | Where to write the JSON result summary. |

### `hamilton-load` (alias: `hamilton`)

Load Hamilton HSR monthly ridership (one agency).

```
python -m transitindex_ingest hamilton-load <csv> [--reset] [--result PATH]
```

| Argument | Type | Default | Meaning |
|---|---|---|---|
| `csv` | path (required) | — | The Hamilton HSR CSV export. |
| `--reset` | flag | off | Delete all existing Hamilton data first, then reload. |
| `--result` | path | `load_hamilton_result.json` | Where to write the JSON result summary. |

> `statcan` and `hamilton` are kept as aliases of the `-load` commands and behave
> identically.

---

## Manual data entry (Excel workbook)

The round-trip for hand-entering annual figures. Full walkthrough in
[managing-data.md](managing-data.md).

### `export-xlsx`

Build an editable `.xlsx` workbook (one row per agency per year), pre-filled with
whatever is already in the database.

```
python -m transitindex_ingest export-xlsx [--out PATH] [--years RANGE]
```

| Argument | Type | Default | Meaning |
|---|---|---|---|
| `--out` | path | `transitindex-data.xlsx` | Output workbook path. |
| `--years` | `YYYY-YYYY` | `2019-2024` | Inclusive year range to include as rows. |

### `import-xlsx`

Read a filled-in workbook, then stage → promote → recompute derived ratios →
refresh ranks.

```
python -m transitindex_ingest import-xlsx <xlsx>
```

| Argument | Type | Default | Meaning |
|---|---|---|---|
| `xlsx` | path (required) | — | The filled-in `.xlsx` workbook. |

---

## PDF extraction (annual reports → review queue)

Pulls metrics out of a PDF into the human review queue. This is tier 2: nothing is
promoted to live data until a reviewer approves it. **Needs `ANTHROPIC_API_KEY`**
plus the `anthropic` and `pypdf` packages (the extractor calls the Anthropic API).

### `pdf`

Extract a PDF's metrics and stage them for review.

```
python -m transitindex_ingest pdf <pdf> --agency SLUG [options]
```

| Argument | Type | Default | Meaning |
|---|---|---|---|
| `pdf` | path (required) | — | The PDF to read. |
| `--agency` | slug (required) | — | Agency slug, e.g. `ttc`. |
| `--doc-type` | string | `annual_report` | Source document type recorded with the values. |
| `--title` | string | none | Source document title. |
| `--url` | string | none | Source document URL. |
| `--dual` | flag | off | Run Opus + Sonnet in parallel and reconcile; disagreements are flagged for review. |
| `--no-prefilter` | flag | off | Send the whole PDF, not just the metric-dense pages. |
| `--max-pages` | int | `15` | Maximum pages sent to the vision model. |

### `pdf-smoke`

Run only the extractor on a PDF and print the values + diagnostics. Touches no
database and stages nothing. Give exactly one of a PDF path or `--url`.

```
python -m transitindex_ingest pdf-smoke [<pdf>] [--url URL] --agency SLUG [options]
```

| Argument | Type | Default | Meaning |
|---|---|---|---|
| `pdf` | path | none | The PDF to read (or use `--url`). |
| `--url` | string | none | Fetch the PDF from this URL instead of a path (needs `httpx`). |
| `--agency` | slug (required) | — | Agency slug, e.g. `ttc`. |
| `--no-verify` | flag | off | Skip the verify second pass. |
| `--model` | string | `claude-sonnet-4-6` | Claude model id. |
| `--dual` | flag | off | Run Opus + Sonnet in parallel and reconcile. |
| `--no-prefilter` | flag | off | Send the whole PDF, not just the metric-dense pages. |
| `--max-pages` | int | `15` | Maximum pages sent to the vision model. |

---

## Maintenance & inspection

### `ranks`

Refresh `core.metric_ranks` for one metric + period.

```
python -m transitindex_ingest ranks --metric CODE --period ID [--scope SCOPE]
```

| Argument | Type | Default | Meaning |
|---|---|---|---|
| `--metric` | string (required) | — | Metric code, e.g. `monthly_ridership`. |
| `--period` | int (required) | — | Reporting-period id. |
| `--scope` | string | `total` | Service scope to rank within. |

### `derived`

Recompute derived ratios (e.g. average fare, farebox recovery) for one agency +
period.

```
python -m transitindex_ingest derived --agency SLUG --period ID
```

| Argument | Type | Default | Meaning |
|---|---|---|---|
| `--agency` | slug (required) | — | Agency slug. |
| `--period` | int (required) | — | Reporting-period id. |

### `pending`

List the rows in `core.pending_values` (the review backlog).

```
python -m transitindex_ingest pending [--status STATUS]
```

| Argument | Type | Default | Meaning |
|---|---|---|---|
| `--status` | string | none (all) | Filter by review status: `pending`, `approved`, `rejected`, or `needs_edit`. |

### `review`

Serve the FastAPI human-review queue. **Needs `REVIEW_API_TOKEN`** (the mutating
endpoints write straight into live data, so the server refuses to start without a
token) plus `uvicorn`.

```
python -m transitindex_ingest review [--host HOST] [--port PORT]
```

| Argument | Type | Default | Meaning |
|---|---|---|---|
| `--host` | string | `127.0.0.1` | Bind address. |
| `--port` | int | `8000` | Bind port. |

---

## Environment

Settings live in the project-root `.env` (read by `config.load_config()`).

| Variable | Needed by | Effect |
|---|---|---|
| `DATABASE_URL` | all commands | Target Postgres database. Unset → in-memory dry run, nothing saved. |
| `ANTHROPIC_API_KEY` | `pdf`, `pdf-smoke` | The extractor calls the Anthropic API; missing → the command errors (exit 2). |
| `REVIEW_API_TOKEN` | `review` | Bearer token guarding the mutating review endpoints; missing → the server refuses to start (exit 2). |

## Related

- [managing-data.md](managing-data.md) — friendly, no-coding guide to the everyday data tasks (the workbook round-trip and the one-click bulk loaders).
- [statcan-loader-design.md](../statcan-loader-design.md) — why the bulk loaders are diff-aware and how the fast path works.
- [ingest/README.md](../ingest/README.md) — the Python package layout and how to run the tests.
- [data-dictionary.md](data-dictionary.md) — what each metric means, its unit, and (for ratios) its formula.
