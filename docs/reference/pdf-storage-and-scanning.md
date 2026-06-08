# PDF storage & scanning

> How raw annual-report PDFs are stored in the cloud and turned into reviewable
> metrics. Status: **living** — matches the shipped `core.documents` catalog,
> the `docs-*` CLI commands, and the review-server console.

## The short version

1. **Raw PDFs live in Supabase Storage**, not on your laptop — a private bucket
   called `annual-reports`, one object per file under `{agency}/{filename}.pdf`.
2. **`core.documents`** is the catalog: one row per PDF (agency, year, doc type,
   `[T]`/`[C]` author label, storage key, source URL, and a `scan_status` of
   `unscanned` → `scanned` / `failed`). The unscanned rows are your work queue.
3. **Scanning** a PDF fetches it from the bucket, runs the existing vision
   extractor, and stages the numbers into the review queue
   (`core.pending_values`). Nothing is published until you approve it in review —
   scanning only *feeds* that queue, it does not bypass it.
4. **PDFs never stay on disk.** A scan downloads the file to a temp file, reads
   it, and deletes it (fetch → scan → discard).

## Everyday tasks

All commands run from the repo (they read `.env` for `DATABASE_URL`,
`SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `ANTHROPIC_API_KEY`).

**See the queue:**
```
python -m transitindex_ingest docs-list                 # everything
python -m transitindex_ingest docs-list --status unscanned
```

**Add a new PDF going forward** (uploads to the bucket + catalogs it):
```
python -m transitindex_ingest docs-upload path/to/stm-2023.pdf \
  --agency stm --year 2023 --doc-type annual_report --author T \
  --source-url https://...
```
`--doc-type` is one of `annual_report`, `financial_statement`, `service_plan`,
`business_plan`, `community_report`. `--author` is `T` (transit-own) or `C`
(city). For a *folder* of conventionally-named files, `docs-sync --pdf-dir DIR`
classifies and uploads them all (idempotent).

**Scan — the easy way (the button):**
```
python -m transitindex_ingest review        # then open http://127.0.0.1:8000/
```
The console lists unscanned PDFs with a **Scan** button. Click it; when it
finishes, the row flips to `scanned` and the extracted values are waiting in the
review queue on the same server.

**Scan — the command-line way:**
```
python -m transitindex_ingest docs-scan 12   # 12 = the catalog id from docs-list
```

**After a scan**, review and approve the staged values as usual (the `/pending`
endpoints / review queue). Approval is the only thing that writes a published
number; scanning never does.

## How it fits together

```
Supabase Storage (annual-reports/)         core.documents (catalog / queue)
        │  download bytes                          │  scan_status
        ▼                                          ▼
   scan_document()  ──run_pdf()──►  core.pending_values  ──approve──►  core.metric_values
                                     (review queue)        (review)     (published)
```

- The catalog (`core.documents`) is **separate** from `core.source_documents`:
  the catalog is the inventory/work-queue of files; `source_documents` is the
  per-value provenance the extractor creates during a scan.
- The Scan endpoint is **open** on the review server because scanning only
  *stages* (the same trust level as running `docs-scan` locally). The
  approve/reject/edit endpoints — which publish live values — keep their
  bearer-token guard. The server binds `127.0.0.1` by default.

## Notes

- **Security:** `SUPABASE_SERVICE_ROLE_KEY` is a master key. It lives only in the
  ingest `.env` (server-side), never in the web app.
- **Author labels & doc types** are derived from `pdfs/MANIFEST.md` by
  `catalog.py`'s filename rules (e.g. `edmonton-ets-service-plan-*` → ETS
  service plan `[T]`; plain `miway-*` → city financial statement `[C]`).
- **Adding new agencies:** `docs-upload`/`docs-sync` skip any agency slug not
  seeded in `core.agencies`; seed the agency first.
