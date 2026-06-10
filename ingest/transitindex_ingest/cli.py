"""Command-line orchestrator wiring the ingestion pieces together.

Thin glue only -- every command composes functions that already exist in the
package; no business logic lives here. The repository is chosen from config: a
PostgresRepository when DATABASE_URL is set, otherwise an ephemeral
InMemoryRepository (a dry run, since nothing persists).

Run as:  python -m transitindex_ingest <command> ...
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import load_config
from .db.memory import InMemoryRepository


def _build_repo():
    """Return (repo, ephemeral). Postgres when DATABASE_URL is set, else in-memory."""
    cfg = load_config()
    if cfg.database_url:
        from .db.postgres import PostgresRepository

        return PostgresRepository(cfg.database_url), False
    return InMemoryRepository(), True


def _note_ephemeral(ephemeral: bool) -> None:
    if ephemeral:
        print(
            "[note] No DATABASE_URL set -- running against an ephemeral in-memory DB. "
            "Nothing is persisted (dry run). Set DATABASE_URL in .env to write Postgres.",
            file=sys.stderr,
        )


def cmd_statcan(args) -> int:
    """SC-307: parse CSV -> stage (tier 0) -> promote -> recompute derived -> rank."""
    from .adapters.statcan_307 import StatCan23100307Adapter
    from .jobs.derived_recompute import recompute_derived
    from .jobs.rank_refresh import refresh_ranks
    from .promotion import promote_approved
    from .refdata import METRICS
    from .staging import stage_records

    repo, ephemeral = _build_repo()
    _note_ephemeral(ephemeral)

    # utf-8-sig: StatCan's CSV export is UTF-8 with a leading BOM; this strips it so
    # the first column header parses as "REF_DATE" rather than a BOM-prefixed key.
    text = Path(args.csv).read_text(encoding="utf-8-sig")
    adapter = StatCan23100307Adapter()
    records = adapter.parse(text)

    pending_ids = stage_records(repo, records, tier=0, feed_code="statcan_307")
    promoted = promote_approved(repo)

    # The (agency, period) and period set the batch touched. Periods are shared
    # across agencies (migration 009), so the same calendar period dedupes to one
    # pid here and all agencies' values rank together in that single cohort.
    periods: set[int] = set()
    agency_periods: set[tuple[str, int]] = set()
    for r in records:
        pid = repo.get_or_create_reporting_period(
            r.period_type, r.period_start, r.period_end, r.period_label
        )
        periods.add(pid)
        agency_periods.add((r.agency_slug, pid))

    # Derived ratios computed from the same-period inputs (e.g. average_fare).
    derived = 0
    warnings: list[str] = []
    for agency_slug, pid in sorted(agency_periods):
        res = recompute_derived(repo, agency_slug, pid)
        derived += len(res.ids)
        warnings.extend(res.warnings)

    # Materialize ranks for every metric in each touched period. StatCan rows are
    # service_scope='total'; refreshing an empty cohort is a harmless no-op.
    for pid in periods:
        for code in METRICS:
            refresh_ranks(repo, code, pid, service_scope="total")

    print(f"parsed        : {len(records)} records")
    print(f"skipped       : {len(adapter.skipped)} unmapped agency row(s)")
    for s in adapter.skipped:
        print(f"  - {s['agency']!r} ({s['measure']}, {s['ref_date']})")
    print(f"staged        : {len(pending_ids)} pending")
    print(f"promoted      : {len(promoted)} into metric_values")
    print(f"derived       : {derived} ratio value(s)")
    if warnings:
        print(f"sanity flags  : {len(warnings)}")
        for w in warnings:
            print(f"  ! {w}")
    print(f"ranks         : refreshed for {len(periods)} period(s)")
    return 0


def cmd_hamilton(args) -> int:
    """Hamilton HSR: parse CSV -> stage (tier 1) -> promote -> recompute derived -> rank."""
    from .adapters.hamilton_hsr import HamiltonHSRAdapter
    from .jobs.derived_recompute import recompute_derived
    from .jobs.rank_refresh import refresh_ranks
    from .promotion import promote_approved
    from .refdata import METRICS
    from .staging import stage_records

    repo, ephemeral = _build_repo()
    _note_ephemeral(ephemeral)

    text = Path(args.csv).read_text(encoding="utf-8")
    adapter = HamiltonHSRAdapter()
    records = adapter.parse(text)

    pending_ids = stage_records(repo, records, tier=1, feed_code="hamilton_open_data")
    promoted = promote_approved(repo)

    periods: set[int] = set()
    agency_periods: set[tuple[str, int]] = set()
    for r in records:
        pid = repo.get_or_create_reporting_period(
            r.period_type, r.period_start, r.period_end, r.period_label
        )
        periods.add(pid)
        agency_periods.add((r.agency_slug, pid))

    derived = 0
    warnings: list[str] = []
    for agency_slug, pid in sorted(agency_periods):
        res = recompute_derived(repo, agency_slug, pid)
        derived += len(res.ids)
        warnings.extend(res.warnings)

    for pid in periods:
        for code in METRICS:
            refresh_ranks(repo, code, pid, service_scope="total")

    print(f"parsed        : {len(records)} records")
    print(f"skipped       : {len(adapter.skipped)} row(s) with missing/bad data")
    for s in adapter.skipped:
        print(f"  - {s}")
    print(f"staged        : {len(pending_ids)} pending")
    print(f"promoted      : {len(promoted)} into metric_values")
    print(f"derived       : {derived} ratio value(s)")
    if warnings:
        print(f"sanity flags  : {len(warnings)}")
        for w in warnings:
            print(f"  ! {w}")
    print(f"ranks         : refreshed for {len(periods)} period(s)")
    return 0


def cmd_pdf(args) -> int:
    """Tier 2: extract metrics from a PDF into the review queue (never promotes)."""
    from .pdf.claude_pdf import ClaudePdfExtractor
    from .pdf.pipeline import SourceRefMeta, run_pdf
    from .validation.flags import validate

    cfg = load_config()
    if not cfg.anthropic_api_key:
        print(
            "error: the PDF pipeline needs ANTHROPIC_API_KEY (set it in .env) and the "
            "anthropic + pypdf packages (pip install anthropic pypdf). "
            "The extractor calls the Anthropic API.",
            file=sys.stderr,
        )
        return 2

    repo, ephemeral = _build_repo()
    _note_ephemeral(ephemeral)

    common = {"prefilter": not args.no_prefilter, "max_pages": args.max_pages}
    if args.dual:
        from .pdf.ensemble import claude_dual

        extractor = claude_dual(cfg.anthropic_api_key, **common)
    else:
        extractor = ClaudePdfExtractor(api_key=cfg.anthropic_api_key, **common)
    meta = SourceRefMeta(document_type=args.doc_type, title=args.title, source_url=args.url)
    try:
        # Row-level validation flags on every staged value. prior_value stays
        # None: the prior-year lookup needs a repo query that does not exist yet.
        pending_ids = run_pdf(
            repo,
            args.pdf,
            args.agency,
            source_ref_meta=meta,
            extractor=extractor,
            validator=lambda repo, record: validate(record),
        )
    except ModuleNotFoundError:
        print(
            "error: the real PDF path needs pypdf and the anthropic SDK "
            "(pip install anthropic pypdf).",
            file=sys.stderr,
        )
        return 2

    print(f"extracted -> staged: {len(pending_ids)} pending (awaiting human review)")
    print("Tier 2: nothing is promoted until a reviewer approves it.")
    return 0


def cmd_pdf_smoke(args) -> int:
    """Run ONLY the extractor on a PDF (no DB, no staging) and print results."""
    from .pdf.claude_pdf import ClaudePdfExtractor
    from .pdf.extractor import ExtractionRequest

    # PDF text (source quotes) carries glyphs the Windows cp1252 console can't
    # encode; print as UTF-8 and replace anything unmappable rather than crash.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    cfg = load_config()
    if not cfg.anthropic_api_key:
        print(
            "error: pdf-smoke needs ANTHROPIC_API_KEY (set it in .env). "
            "It calls the Anthropic API to read the PDF.",
            file=sys.stderr,
        )
        return 2

    if bool(args.pdf) == bool(args.url):
        print("error: give exactly one of a PDF path or --url.", file=sys.stderr)
        return 2

    # Source the PDF bytes from a path or a URL.
    if args.url:
        try:
            import httpx  # lazy: only when fetching
        except ModuleNotFoundError:
            print("error: fetching --url needs httpx (pip install httpx).", file=sys.stderr)
            return 2
        try:
            resp = httpx.get(args.url, follow_redirects=True, timeout=60)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            print(f"error: could not fetch {args.url}: {exc}", file=sys.stderr)
            return 2
        pdf_bytes = resp.content
        if not pdf_bytes.startswith(b"%PDF"):
            print(
                f"error: {args.url} did not return a PDF "
                f"(content-type: {resp.headers.get('content-type', 'unknown')}).",
                file=sys.stderr,
            )
            return 2
    else:
        pdf_bytes = Path(args.pdf).read_bytes()

    common = {"prefilter": not args.no_prefilter, "max_pages": args.max_pages}
    if args.dual:
        from .pdf.ensemble import claude_dual

        extractor = claude_dual(cfg.anthropic_api_key, **common)
    else:
        model_kw = {"model": args.model} if args.model else {}
        extractor = ClaudePdfExtractor(
            api_key=cfg.anthropic_api_key, verify=not args.no_verify, **model_kw, **common
        )
    try:
        result = extractor.extract(
            ExtractionRequest(agency_slug=args.agency, pdf_bytes=pdf_bytes)
        )
    except ModuleNotFoundError:
        print(
            "error: the real PDF path needs pypdf and the anthropic SDK "
            "(pip install anthropic pypdf httpx).",
            file=sys.stderr,
        )
        return 2

    print(f"{len(result.values)} value(s) extracted:\n")
    for v in result.values:
        period = (
            f"{v.period_year}"
            if v.period_kind == "annual"
            else f"{v.period_year}-{v.period_month:02d}"
        )
        print(
            f"  {v.metric_code} = {v.value} {v.unit}  "
            f"[{v.period_kind} {period}]  p.{v.page_number}  conf={v.confidence}"
        )
        if v.source_quote:
            print(f"      quote: {v.source_quote!r}")
        if v.note:
            print(f"      note:  {v.note}")
    d = result.diagnostics
    print("\ndiagnostics:")
    if d.get("extractor") == "dual_model":
        print(f"  models        : {', '.join(d.get('models', []))}")
        print(f"  per-model     : {d.get('per_model_counts')}")
        print(f"  reconciled    : {d.get('reconciled_count')}")
        print(f"  needs_review  : {d.get('needs_review')} (flagged for a human)")
        if d.get("errors"):
            print(f"  model errors  : {d.get('errors')}")
    else:
        print(f"  model         : {d.get('model')}")
        print(f"  page_count    : {d.get('page_count')}")
        print(f"  pages_sent    : {d.get('pages_sent')} {d.get('pages_selected') or ''}")
        print(f"  chunks        : {d.get('chunks')}")
        print(f"  verify_dropped: {d.get('verify_dropped')}")
    print(f"  est_cost_usd  : ~${d.get('est_cost_usd', 0):.4f}")
    return 0


def _build_storage():
    """Return a SupabaseStorage from config, or None after printing why not."""
    from .storage import SupabaseStorage

    try:
        return SupabaseStorage.from_config(load_config())
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return None


def cmd_docs_sync(args) -> int:
    """Upload local PDFs to cloud storage and (re)build the core.documents catalog."""
    from . import catalog

    if args.dry_run:
        recognised, skipped = catalog.plan_local_pdfs(args.pdf_dir)
        print(f"would upload : {len(recognised)} PDF(s)")
        for fn, spec in recognised:
            print(f"  {fn:42s} -> {spec.agency_slug:18s} {spec.year} {spec.doc_type} [{spec.author_label}]")
        print(f"skipped      : {len(skipped)} (not launch-set files)")
        for fn, reason in skipped:
            print(f"  - {fn}: {reason}")
        print("\n(dry run -- nothing uploaded; drop --dry-run to do it for real.)")
        return 0

    repo, ephemeral = _build_repo()
    _note_ephemeral(ephemeral)
    storage = _build_storage()
    if storage is None:
        return 2

    summary = catalog.sync_local_pdfs(repo, storage, args.pdf_dir)
    print(f"bucket        : {storage.bucket}")
    print(f"uploaded      : {summary['uploaded']} PDF(s) -> catalog rows")
    print(f"skipped       : {len(summary['skipped'])} (not launch-set files)")
    for fn, reason in summary["skipped"]:
        print(f"  - {fn}: {reason}")
    print("next step     : python -m transitindex_ingest docs-list  (see the scan queue)")
    return 0


def cmd_docs_upload(args) -> int:
    """Upload one PDF (with explicit metadata) and catalog it. The go-forward path."""
    from . import catalog
    from .storage import sha256_hex

    repo, ephemeral = _build_repo()
    _note_ephemeral(ephemeral)
    storage = _build_storage()
    if storage is None:
        return 2

    try:
        agency_id = repo.agency_id(args.agency)
    except ValueError:
        print(f"error: unknown agency slug {args.agency!r} (must be a seeded agency).", file=sys.stderr)
        return 2

    data = Path(args.pdf).read_bytes()
    key = catalog.storage_key_for(args.agency, Path(args.pdf).name)
    storage.ensure_bucket()
    storage.upload(key, data)
    doc_id = repo.upsert_document(
        agency_id=agency_id,
        year=args.year,
        doc_type=args.doc_type,
        author_label=args.author,
        storage_key=key,
        source_url=args.source_url,
        file_hash=sha256_hex(data),
        file_bytes=len(data),
    )
    print(f"uploaded      : {key} ({len(data)} bytes)")
    print(f"catalog id    : {doc_id} (status unscanned)")
    return 0


def cmd_docs_list(args) -> int:
    """List the core.documents catalog (the scan queue)."""
    repo, ephemeral = _build_repo()
    _note_ephemeral(ephemeral)
    slug_by_id = {repo.agency_id(s): s for s in _seeded_slugs(repo)}
    rows = repo.list_documents(status=args.status)
    label = f" with status={args.status}" if args.status else ""
    print(f"{len(rows)} document(s){label}")
    for d in rows:
        agency = slug_by_id.get(d.agency_id, f"agency#{d.agency_id}")
        extra = ""
        if d.scan_status == "scanned" and d.staged_count is not None:
            extra = f" staged={d.staged_count}"
        elif d.scan_status == "failed" and d.last_error:
            extra = f" error={d.last_error[:60]!r}"
        print(f"  #{d.id:<3} [{d.scan_status:9}] {agency:18} {d.year} {d.doc_type} [{d.author_label}]{extra}")
    return 0


def cmd_docs_scan(args) -> int:
    """Scan one cataloged document (CLI twin of the console Scan button)."""
    from .scan import scan_document

    cfg = load_config()
    if not cfg.anthropic_api_key:
        print("error: scanning needs ANTHROPIC_API_KEY in .env (it calls the Anthropic API).", file=sys.stderr)
        return 2
    repo, ephemeral = _build_repo()
    _note_ephemeral(ephemeral)
    storage = _build_storage()
    if storage is None:
        return 2

    result = scan_document(repo, storage, args.id, cfg=cfg)
    if result["ok"]:
        print(f"scanned       : doc #{args.id} -> {result['staged_count']} pending value(s) for review")
        print("Tier 2: nothing is promoted until a reviewer approves it.")
        return 0
    print(f"scan FAILED   : doc #{args.id}: {result['error']}", file=sys.stderr)
    return 1


def cmd_docs_verify(args) -> int:
    """Download every cataloged file and confirm its hash matches the cloud copy."""
    from . import catalog

    repo, ephemeral = _build_repo()
    _note_ephemeral(ephemeral)
    storage = _build_storage()
    if storage is None:
        return 2

    result = catalog.verify_uploads(repo, storage)
    print(f"checked       : {result['checked']} file(s)")
    print(f"mismatches    : {len(result['mismatches'])}")
    for k in result["mismatches"]:
        print(f"  ! {k}")
    if result["missing_hash"]:
        print(f"missing hash  : {len(result['missing_hash'])}")
        for k in result["missing_hash"]:
            print(f"  ? {k}")
    print(f"result        : {'OK -- safe to delete local copies' if result['ok'] else 'NOT OK -- keep local copies'}")
    return 0 if result["ok"] else 1


def _seeded_slugs(repo) -> list[str]:
    """The launch agency slugs, for id->slug display."""
    from .refdata import AGENCIES

    out = []
    for slug in AGENCIES:
        try:
            repo.agency_id(slug)
            out.append(slug)
        except ValueError:
            continue
    return out


def cmd_export_xlsx(args) -> int:
    """Build the editable per-agency time-series .xlsx workbook (one tab per agency)."""
    from . import workbook

    repo, ephemeral = _build_repo()
    _note_ephemeral(ephemeral)

    years = _parse_years(args.years)
    summary = workbook.export_workbook(repo, args.out, years)

    n_years = len(summary["years"])
    print(f"workbook      : {summary['path']}")
    print(f"agencies      : {summary['agencies']} tab(s) x {n_years} year(s)")
    print(f"per tab       : {summary['metric_rows']} metric rows + {summary['fleet_modes']} fleet modes")
    print(f"filled cells  : {summary['filled_cells']} (pre-filled from the database)")
    print(
        "next step     : Open it, fill the white cells, then: "
        f"python -m transitindex_ingest import-xlsx {summary['path']}"
    )
    return 0


def cmd_import_xlsx(args) -> int:
    """Read a filled-in workbook -> stage -> promote -> roll up -> recompute derived -> rank."""
    from . import workbook

    repo, ephemeral = _build_repo()
    _note_ephemeral(ephemeral)

    summary = workbook.import_workbook(repo, args.xlsx)

    print(f"staged        : {summary['staged']} pending")
    print(f"promoted      : {summary['promoted']} into metric_values")
    print(f"rolled up     : {summary['rolled']} monthly->annual value(s)")
    print(f"derived       : {summary['derived']} ratio value(s)")
    print(f"ranks         : refreshed for {summary['periods']} period(s)")
    if summary["warnings"]:
        print(f"sanity flags  : {len(summary['warnings'])}")
        for w in summary["warnings"]:
            print(f"  ! {w}")
    return 0


def _parse_years(spec: str) -> list[int]:
    """Parse a '2019-2024' range (inclusive) into a list of ints."""
    start_str, _, end_str = spec.partition("-")
    start, end = int(start_str), int(end_str)
    return list(range(start, end + 1))


def cmd_ranks(args) -> int:
    """Refresh core.metric_ranks for one metric + period."""
    from .jobs.rank_refresh import refresh_ranks

    repo, ephemeral = _build_repo()
    _note_ephemeral(ephemeral)
    refresh_ranks(repo, args.metric, args.period, service_scope=args.scope)
    print(f"ranks refreshed: {args.metric} period={args.period} scope={args.scope}")
    return 0


def cmd_derived(args) -> int:
    """Recompute derived ratios for one agency + period."""
    from .jobs.derived_recompute import recompute_derived

    repo, ephemeral = _build_repo()
    _note_ephemeral(ephemeral)
    res = recompute_derived(repo, args.agency, args.period)
    print(f"derived written: {len(res.ids)}")
    for w in res.warnings:
        print(f"  ! {w}")
    return 0


def cmd_pending(args) -> int:
    """List core.pending_values rows (the review backlog)."""
    repo, ephemeral = _build_repo()
    _note_ephemeral(ephemeral)
    rows = repo.list_pending_values(status=args.status)
    label = f" with status={args.status}" if args.status else ""
    print(f"{len(rows)} pending value(s){label}")
    for r in rows:
        print(
            f"  #{r.id} agency={r.agency_id} metric={r.metric_id} "
            f"value={r.value} status={r.review_status} flags={r.flags}"
        )
    return 0


def cmd_review(args) -> int:
    """Serve the FastAPI human review queue."""
    cfg = load_config()
    if not cfg.review_api_token:
        print(
            "error: the review server needs REVIEW_API_TOKEN (set it in .env). "
            "Approving or editing writes straight into live metric_values, so the "
            "mutating endpoints require a bearer token -- refusing to serve an open door.",
            file=sys.stderr,
        )
        return 2

    repo, ephemeral = _build_repo()
    _note_ephemeral(ephemeral)
    if ephemeral:
        print(
            "[warn] Serving the review queue against an ephemeral in-memory DB -- it starts "
            "empty and changes are lost on exit. Set DATABASE_URL for real review.",
            file=sys.stderr,
        )
    try:
        import uvicorn
    except ImportError:
        print("error: the review server needs uvicorn (pip install uvicorn).", file=sys.stderr)
        return 2
    from .review.app import create_app

    # Wire the documents-console Scan button to the real scan path when storage +
    # the Anthropic key are configured. Missing keys -> scanner=None: review still
    # works and the console shows a "scanning unavailable" notice (no crash).
    scanner = None
    if cfg.supabase_url and cfg.supabase_service_role_key and cfg.anthropic_api_key:
        from .scan import scan_document
        from .storage import SupabaseStorage

        storage = SupabaseStorage.from_config(cfg)
        scanner = lambda document_id: scan_document(repo, storage, document_id, cfg=cfg)
    else:
        print(
            "[note] documents console: Scan disabled until SUPABASE_URL, "
            "SUPABASE_SERVICE_ROLE_KEY and ANTHROPIC_API_KEY are all set in .env.",
            file=sys.stderr,
        )

    uvicorn.run(
        create_app(repo, token=cfg.review_api_token, scanner=scanner),
        host=args.host,
        port=args.port,
    )
    return 0


def cmd_statcan_load(args) -> int:
    """Fast bulk load of StatCan 23-10-0307 (replaces the slow cmd_statcan)."""
    import json as _json
    from .jobs.bulk_load import load_statcan

    repo, ephemeral = _build_repo()
    _note_ephemeral(ephemeral)

    result = load_statcan(repo, Path(args.csv), reset=getattr(args, "reset", False))

    result_path = Path(getattr(args, "result", "load_statcan_result.json"))
    result_path.write_text(_json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    print(f"result written to {result_path} (ok={result.ok})", flush=True)
    return 0 if result.ok else 1


def cmd_hamilton_load(args) -> int:
    """Fast bulk load of Hamilton HSR (replaces the slow cmd_hamilton)."""
    import json as _json
    from .jobs.bulk_load import load_hamilton

    repo, ephemeral = _build_repo()
    _note_ephemeral(ephemeral)

    result = load_hamilton(repo, Path(args.csv), reset=getattr(args, "reset", False))

    result_path = Path(getattr(args, "result", "load_hamilton_result.json"))
    result_path.write_text(_json.dumps(result.to_dict(), indent=2), encoding="utf-8")
    print(f"result written to {result_path} (ok={result.ok})", flush=True)
    return 0 if result.ok else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="transitindex_ingest", description="TransitIndex ingestion pipeline."
    )
    sub = p.add_subparsers(dest="command", required=True)

    # statcan and statcan-load are the same fast path. statcan is kept for
    # backwards compatibility; statcan-load adds --reset and --result flags.
    for name, help_str in [
        ("statcan", "Fast bulk load of StatCan 23-10-0307 CSV."),
        ("statcan-load", "Fast bulk load of StatCan 23-10-0307 CSV (full options)."),
    ]:
        sp = sub.add_parser(name, help=help_str)
        sp.add_argument("csv", help="Path to the 23-10-0307 CSV export.")
        sp.add_argument(
            "--reset",
            action="store_true",
            default=False,
            help="Wipe all existing StatCan data before loading (initial/forced reload).",
        )
        sp.add_argument(
            "--result",
            default="load_statcan_result.json",
            help="Path to write the JSON result summary.",
        )
        sp.set_defaults(func=cmd_statcan_load)

    for name, help_str in [
        ("hamilton", "Fast bulk load of Hamilton HSR ArcGIS CSV."),
        ("hamilton-load", "Fast bulk load of Hamilton HSR ArcGIS CSV (full options)."),
    ]:
        hp = sub.add_parser(name, help=help_str)
        hp.add_argument("csv", help="Path to the Hamilton HSR CSV export.")
        hp.add_argument(
            "--reset",
            action="store_true",
            default=False,
            help="Wipe all existing Hamilton data before loading.",
        )
        hp.add_argument(
            "--result",
            default="load_hamilton_result.json",
            help="Path to write the JSON result summary.",
        )
        hp.set_defaults(func=cmd_hamilton_load)

    pp = sub.add_parser(
        "pdf", help="Extract metrics from a PDF (annual report/budget) into the review queue."
    )
    pp.add_argument("pdf", help="Path to the PDF.")
    pp.add_argument("--agency", required=True, help="Agency slug (e.g. ttc).")
    pp.add_argument(
        "--doc-type",
        dest="doc_type",
        default="annual_report",
        help="source document_type (default: annual_report).",
    )
    pp.add_argument("--title", default=None)
    pp.add_argument("--url", default=None)
    pp.add_argument(
        "--dual",
        action="store_true",
        help="Run Opus + Sonnet in parallel and reconcile (disagreements flagged for review).",
    )
    pp.add_argument("--no-prefilter", action="store_true", help="Send the whole PDF, not just metric-dense pages.")
    pp.add_argument("--max-pages", dest="max_pages", type=int, default=15, help="Max pages sent to vision (default 15).")
    pp.set_defaults(func=cmd_pdf)

    sm = sub.add_parser(
        "pdf-smoke",
        help="Run only the PDF extractor (no DB) and print values + diagnostics.",
    )
    sm.add_argument("pdf", nargs="?", default=None, help="Path to the PDF (or use --url).")
    sm.add_argument("--url", default=None, help="Fetch the PDF from this URL instead of a path.")
    sm.add_argument("--agency", required=True, help="Agency slug (e.g. ttc).")
    sm.add_argument("--no-verify", action="store_true", help="Skip the verify second pass.")
    sm.add_argument("--model", default=None, help="Claude model id (default: claude-sonnet-4-6).")
    sm.add_argument(
        "--dual",
        action="store_true",
        help="Run Opus + Sonnet in parallel and reconcile (disagreements flagged for review).",
    )
    sm.add_argument("--no-prefilter", action="store_true", help="Send the whole PDF, not just metric-dense pages.")
    sm.add_argument("--max-pages", dest="max_pages", type=int, default=15, help="Max pages sent to vision (default 15).")
    sm.set_defaults(func=cmd_pdf_smoke)

    ep = sub.add_parser(
        "export-xlsx", help="Export an editable .xlsx workbook for manual data entry."
    )
    ep.add_argument("--out", default="transitindex-data.xlsx", help="Output path (default: transitindex-data.xlsx).")
    ep.add_argument("--years", default="2019-2024", help="Inclusive year range, e.g. 2019-2024 (default).")
    ep.set_defaults(func=cmd_export_xlsx)

    ip = sub.add_parser(
        "import-xlsx", help="Import a filled-in workbook: stage, promote, recompute derived, rank."
    )
    ip.add_argument("xlsx", help="Path to the filled-in .xlsx workbook.")
    ip.set_defaults(func=cmd_import_xlsx)

    rp = sub.add_parser("ranks", help="Refresh metric_ranks for a metric+period.")
    rp.add_argument("--metric", required=True)
    rp.add_argument("--period", type=int, required=True)
    rp.add_argument("--scope", default="total")
    rp.set_defaults(func=cmd_ranks)

    dp = sub.add_parser("derived", help="Recompute derived ratios for an agency+period.")
    dp.add_argument("--agency", required=True)
    dp.add_argument("--period", type=int, required=True)
    dp.set_defaults(func=cmd_derived)

    lp = sub.add_parser("pending", help="List core.pending_values rows.")
    lp.add_argument(
        "--status", default=None, help="filter by review_status (pending/approved/rejected/needs_edit)."
    )
    lp.set_defaults(func=cmd_pending)

    vp = sub.add_parser("review", help="Serve the review queue + documents/scan console.")
    vp.add_argument("--host", default="127.0.0.1")
    vp.add_argument("--port", type=int, default=8000)
    vp.set_defaults(func=cmd_review)

    _DOC_TYPES = [
        "annual_report", "financial_statement", "service_plan",
        "business_plan", "community_report",
    ]

    ds = sub.add_parser("docs-sync", help="Upload local PDFs to cloud storage + build the catalog.")
    ds.add_argument("--pdf-dir", dest="pdf_dir", default="pdfs", help="Folder of PDFs (default: pdfs).")
    ds.add_argument("--dry-run", action="store_true", help="Classify + report only; upload nothing.")
    ds.set_defaults(func=cmd_docs_sync)

    du = sub.add_parser("docs-upload", help="Upload ONE PDF with explicit metadata + catalog it.")
    du.add_argument("pdf", help="Path to the PDF.")
    du.add_argument("--agency", required=True, help="Agency slug (e.g. ttc).")
    du.add_argument("--year", type=int, required=True, help="Nominal report year.")
    du.add_argument("--doc-type", dest="doc_type", required=True, choices=_DOC_TYPES)
    du.add_argument("--author", required=True, choices=["T", "C"], help="T = transit-own, C = city.")
    du.add_argument("--source-url", dest="source_url", default=None, help="Where the PDF came from.")
    du.set_defaults(func=cmd_docs_upload)

    dl = sub.add_parser("docs-list", help="List the documents catalog (the scan queue).")
    dl.add_argument("--status", default=None, help="Filter by scan_status (unscanned/scanned/failed).")
    dl.set_defaults(func=cmd_docs_list)

    dsc = sub.add_parser("docs-scan", help="Scan one cataloged document (stage values for review).")
    dsc.add_argument("id", type=int, help="Catalog document id (see docs-list).")
    dsc.set_defaults(func=cmd_docs_scan)

    dv = sub.add_parser("docs-verify", help="Verify each cataloged file hashes to its cloud copy.")
    dv.set_defaults(func=cmd_docs_verify)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
