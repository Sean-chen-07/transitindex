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

    text = Path(args.csv).read_text(encoding="utf-8")
    adapter = StatCan23100307Adapter()
    records = adapter.parse(text)

    pending_ids = stage_records(repo, records, tier=0, feed_code="statcan_307")
    promoted = promote_approved(repo)

    # The (agency, period) and period set the batch touched.
    periods: set[int] = set()
    agency_periods: set[tuple[str, int]] = set()
    for r in records:
        aid = repo.agency_id(r.agency_slug)
        pid = repo.get_or_create_reporting_period(
            aid, r.period_type, r.period_start, r.period_end, r.period_label
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
    print(f"skipped (geo) : {len(adapter.skipped)} unmapped system row(s)")
    for s in adapter.skipped:
        print(f"  - {s['geo']!r} ({s['measure']}, {s['ref_date']})")
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
        pending_ids = run_pdf(repo, args.pdf, args.agency, source_ref_meta=meta, extractor=extractor)
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

    uvicorn.run(create_app(repo), host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="transitindex_ingest", description="TransitIndex ingestion pipeline."
    )
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser(
        "statcan", help="Parse a StatCan 23-10-0307 CSV, stage, promote, rank, derive."
    )
    sp.add_argument("csv", help="Path to the 23-10-0307 CSV export.")
    sp.set_defaults(func=cmd_statcan)

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

    vp = sub.add_parser("review", help="Serve the FastAPI human review queue.")
    vp.add_argument("--host", default="127.0.0.1")
    vp.add_argument("--port", type=int, default=8000)
    vp.set_defaults(func=cmd_review)

    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
