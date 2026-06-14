"""Scratch harness: populate the DB from PDFs with CLAUDE-as-the-model (no API).

The normal scan path calls the Anthropic API to read each PDF. This harness swaps
that one step out: Claude (in the coding session) reads the PDF's text/figures and
hands back the same `record_metrics` rows the API would, then we stage them through
the EXACT same pipeline (scan_document -> run_pdf -> core.pending_values), so nothing
about the review/promotion safety model changes. No ANTHROPIC_API_KEY is used.

Two subcommands:
  fetch <doc_id>  download the PDF from Supabase Storage, convert its text layer to
                  markdown (markitdown, offline/free), write _manual/<id>.md and
                  _manual/<id>.pdf, and report page count + which pages are scanned.
  stage <doc_id>  read _manual/<id>.rows.json (the rows Claude produced), build the
                  ExtractedValues with the real _row_to_value (scale/sign/quote caps),
                  apply the chunked_hybrid drop filters, and stage via scan_document.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# UTF-8 console: source quotes carry glyphs cp1252 can't encode.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

from transitindex_ingest.config import load_config
from transitindex_ingest.storage import SupabaseStorage

_MANUAL = Path(__file__).resolve().parent / "_manual"


def _repo():
    cfg = load_config()
    if not cfg.database_url:
        raise SystemExit("error: DATABASE_URL not set in .env")
    from transitindex_ingest.db.postgres import PostgresRepository

    return PostgresRepository(cfg.database_url), cfg


def _slug_map(repo) -> dict:
    """agency_id -> slug for the seeded launch agencies."""
    from transitindex_ingest.refdata import AGENCIES

    out = {}
    for slug in AGENCIES:
        try:
            out[repo.agency_id(slug)] = slug
        except ValueError:
            continue
    return out


def cmd_prep(ids: list[int]) -> int:
    """Pre-fetch PDFs -> markdown + a manifest the workflow agents read.

    With no ids, preps every unscanned catalog document. Writes per doc:
    _manual/<id>.md, _manual/<id>.pdf; plus _manual/contract.txt (the real
    extractor's full system prompt + metric canon) and _manual/manifest.json
    (one entry per doc with its agency/year/type + the exact per-doc framing
    string the paid extractor would prepend, so agents behave identically).
    """
    from io import BytesIO

    from pypdf import PdfReader
    from transitindex_ingest.pdf.chunked_hybrid import ChunkedHybridExtractor
    from transitindex_ingest.pdf.extractor import ExtractionRequest
    from transitindex_ingest.pdf.markitdown_path import _to_markdown

    repo, cfg = _repo()
    storage = SupabaseStorage.from_config(cfg)
    slug_by_id = _slug_map(repo)

    if ids:
        docs = [repo.get_document(i) for i in ids]
        docs = [d for d in docs if d is not None]
    else:
        docs = repo.list_documents(status="unscanned")

    # The real extractor builds the authoritative system prompt (with the metric
    # canon) and a per-doc intro; reuse them verbatim so agents == paid path.
    ext = ChunkedHybridExtractor(api_key=None)
    _MANUAL.mkdir(exist_ok=True)
    (_MANUAL / "contract.txt").write_text(ext._system_prompt, encoding="utf-8")

    manifest = []
    for doc in docs:
        slug = slug_by_id.get(doc.agency_id, f"agency#{doc.agency_id}")
        try:
            data = storage.download(doc.storage_key)
            (_MANUAL / f"{doc.id}.pdf").write_bytes(data)
            md = _to_markdown(data)
            (_MANUAL / f"{doc.id}.md").write_text(md, encoding="utf-8")
            reader = PdfReader(BytesIO(data))
            scanned = [
                i + 1
                for i, p in enumerate(reader.pages)
                if len((p.extract_text() or "").strip()) < 120
            ]
            intro = ext._agency_intro(
                ExtractionRequest(
                    agency_slug=slug,
                    doc_type=doc.doc_type,
                    author_label=doc.author_label,
                    doc_year=doc.year,
                )
            )
            manifest.append({
                "id": doc.id,
                "agency": slug,
                "year": doc.year,
                "doc_type": doc.doc_type,
                "author_label": doc.author_label,
                "pages": len(reader.pages),
                "scanned_pages": scanned,
                "md_chars": len(md),
                "intro": intro,
                "error": None,
            })
            print(f"  prepped #{doc.id:<3} {slug:18} {doc.year} {doc.doc_type:20} "
                  f"pages={len(reader.pages):>3} scanned={len(scanned):>2} md={len(md)}")
        except Exception as exc:
            manifest.append({"id": doc.id, "agency": slug, "year": doc.year,
                             "doc_type": doc.doc_type, "author_label": doc.author_label,
                             "error": f"{type(exc).__name__}: {exc}"})
            print(f"  FAILED  #{doc.id}: {type(exc).__name__}: {exc}", file=sys.stderr)

    (_MANUAL / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    ok = [m for m in manifest if not m.get("error")]
    print(f"\nprepped {len(ok)}/{len(manifest)} docs -> _manual/manifest.json")
    return 0


def cmd_fetch(doc_id: int) -> int:
    from io import BytesIO

    from pypdf import PdfReader
    from transitindex_ingest.pdf.markitdown_path import _to_markdown

    repo, cfg = _repo()
    storage = SupabaseStorage.from_config(cfg)
    doc = repo.get_document(doc_id)
    if doc is None:
        raise SystemExit(f"error: unknown document id {doc_id}")

    data = storage.download(doc.storage_key)
    _MANUAL.mkdir(exist_ok=True)
    (_MANUAL / f"{doc_id}.pdf").write_bytes(data)

    md = _to_markdown(data)
    (_MANUAL / f"{doc_id}.md").write_text(md, encoding="utf-8")

    reader = PdfReader(BytesIO(data))
    scanned = [
        i + 1
        for i, p in enumerate(reader.pages)
        if len((p.extract_text() or "").strip()) < 120
    ]
    print(f"doc #{doc_id}: {doc.storage_key}")
    print(f"  pages         : {len(reader.pages)}")
    print(f"  scanned pages : {scanned or 'none (full text layer)'}")
    print(f"  markdown chars: {len(md)}")
    print(f"  wrote         : _manual/{doc_id}.md  and  _manual/{doc_id}.pdf")
    return 0


def _stage_doc(repo, storage, cfg, doc_id: int, rows: list) -> dict:
    """Build values from rows, apply the chunked_hybrid drop filters, and stage
    through scan_document (FakeExtractor) -> core.pending_values. Returns the
    scan_document result plus raw/kept counts."""
    from transitindex_ingest.pdf.chunked_hybrid import (
        CONFIDENCE_FLOOR,
        DROPPED_BASES,
        DROPPED_SCOPES,
    )
    from transitindex_ingest.pdf.extractor import FakeExtractor
    from transitindex_ingest.pdf.llm import _row_to_value
    from transitindex_ingest.scan import scan_document

    values = []
    for r in rows:
        try:
            values.append(_row_to_value(r))
        except (KeyError, ValueError, TypeError) as exc:
            print(f"  ! #{doc_id} skipped a row: {type(exc).__name__}: {exc}", file=sys.stderr)
    n_raw = len(values)
    # Same post-merge drops chunked_hybrid applies: sub-floor noise, out-of-scope
    # (single-mode/city-wide) figures, and budget/forecast (non-actual) figures.
    values = [v for v in values if v.confidence >= CONFIDENCE_FLOOR]
    values = [
        v
        for v in values
        if v.service_scope not in DROPPED_SCOPES and v.basis not in DROPPED_BASES
    ]
    result = scan_document(repo, storage, doc_id, extractor=FakeExtractor(values), cfg=cfg)
    result = dict(result)
    result["n_raw"] = n_raw
    result["n_kept"] = len(values)
    return result


def cmd_stage(doc_id: int) -> int:
    rows_path = _MANUAL / f"{doc_id}.rows.json"
    if not rows_path.is_file():
        raise SystemExit(f"error: {rows_path} not found (write the rows JSON first)")
    rows = json.loads(rows_path.read_text(encoding="utf-8"))
    repo, cfg = _repo()
    storage = SupabaseStorage.from_config(cfg)
    result = _stage_doc(repo, storage, cfg, doc_id, rows)
    print(f"doc #{doc_id}: rows={result['n_raw']} -> kept={result['n_kept']} -> {result}")
    return 0 if result.get("ok") else 1


def cmd_ingest(output_path: str) -> int:
    """Stage every doc in a workflow output file into core.pending_values.

    Reads the wrapped workflow result ({summary, logs, result:[{id, values}...]}),
    writes each doc's _manual/<id>.rows.json, and stages it. One repo/storage for
    the whole batch (DB writes are serialized here, which is what we want)."""
    obj = json.loads(Path(output_path).read_text(encoding="utf-8"))
    docs = obj.get("result") if isinstance(obj, dict) else obj
    if not isinstance(docs, list):
        raise SystemExit(f"error: no result list in {output_path}")

    repo, cfg = _repo()
    storage = SupabaseStorage.from_config(cfg)

    total_staged = 0
    skipped: list[int] = []
    print(f"{'doc':>5}  raw kept staged  ok")
    for d in docs:
        doc_id = d["id"]
        # An agent that errored (e.g. hit the session limit) returns error+empty.
        # Do NOT stage it -- that would mark the catalog row 'scanned' with 0 values
        # and hide it from a retry. Leave it 'unscanned'.
        if d.get("error"):
            skipped.append(doc_id)
            print(f"  #{doc_id:<3} SKIP (agent error: {str(d.get('error'))[:50]})")
            continue
        # Idempotency: never re-stage a doc already marked scanned (a retry run
        # re-emits the whole batch; only the previously-failed docs should land).
        existing = repo.get_document(doc_id)
        if existing is not None and existing.scan_status == "scanned":
            skipped.append(doc_id)
            print(f"  #{doc_id:<3} SKIP (already scanned, staged={existing.staged_count})")
            continue
        rows = d.get("values") or []
        (_MANUAL / f"{doc_id}.rows.json").write_text(
            json.dumps(rows, indent=2), encoding="utf-8"
        )
        res = _stage_doc(repo, storage, cfg, doc_id, rows)
        staged = res.get("staged_count", 0)
        total_staged += staged
        flag = "ok" if res.get("ok") else f"FAIL {res.get('error')}"
        print(f"  #{doc_id:<3} {res['n_raw']:>3} {res['n_kept']:>4} {staged:>6}  {flag}")
    print(f"\nTOTAL staged into pending_values: {total_staged}")
    if skipped:
        print(f"SKIPPED (left unscanned for retry): {sorted(skipped)}")
    return 0


def main(argv) -> int:
    if not argv:
        raise SystemExit("usage: _manual_scan.py [prep|fetch|stage|ingest] [args...]")
    cmd = argv[0]
    if cmd == "prep":
        return cmd_prep([int(x) for x in argv[1:]])
    if cmd == "fetch":
        return cmd_fetch(int(argv[1]))
    if cmd == "stage":
        return cmd_stage(int(argv[1]))
    if cmd == "ingest":
        return cmd_ingest(argv[1])
    raise SystemExit(f"unknown command {cmd!r}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
