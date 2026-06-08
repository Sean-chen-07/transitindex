"""The operator console: a documents queue with Scan buttons.

Mounted onto the same FastAPI app as the JSON review queue, so one process
(`python -m transitindex_ingest review`) serves both. The operator opens
http://127.0.0.1:8000/ , sees unscanned PDFs, and clicks Scan.

Trust model: scanning only STAGES values into core.pending_values -- the exact
same tier-2 action as running `python -m transitindex_ingest pdf` locally, which
needs no token. So these routes are open, consistent with "staging is open,
promotion is guarded". The approve/reject/edit endpoints (which write live
metric_values, Invariant #1) keep their bearer-token guard. The server binds
127.0.0.1 by default; that localhost assumption is what keeps the open scan
endpoint (which spends Anthropic credits) from being world-reachable.
"""

from __future__ import annotations

import html
from typing import Callable, Optional
from urllib.parse import urlencode

from ..refdata import AGENCIES

# scanner(document_id) -> {"ok": bool, "staged_count": int, "error": str|None}
Scanner = Callable[[int], dict]

_STATUS_BADGE = {
    "unscanned": "#b45309",  # amber
    "scanned": "#15803d",    # green
    "failed": "#b91c1c",     # red
}


def _page(body: str) -> str:
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>TransitIndex — documents</title>"
        "<style>"
        "body{font:15px/1.5 system-ui,sans-serif;margin:2rem auto;max-width:920px;color:#1f2937}"
        "h1{font-size:1.4rem}table{border-collapse:collapse;width:100%}"
        "th,td{text-align:left;padding:.5rem .6rem;border-bottom:1px solid #e5e7eb}"
        "th{font-size:.78rem;text-transform:uppercase;letter-spacing:.03em;color:#6b7280}"
        ".badge{font-size:.72rem;font-weight:600;color:#fff;padding:.1rem .45rem;border-radius:.4rem}"
        "button{font:inherit;padding:.3rem .8rem;border:0;border-radius:.4rem;background:#2563eb;color:#fff;cursor:pointer}"
        "button:hover{background:#1d4ed8}.muted{color:#6b7280}.note{background:#f0fdf4;border:1px solid #bbf7d0;"
        "padding:.6rem .8rem;border-radius:.5rem;margin:1rem 0}.err{background:#fef2f2;border-color:#fecaca}"
        "</style></head><body>" + body + "</body></html>"
    )


def mount_console(app, repo, *, scanner: Optional[Scanner] = None) -> None:
    """Add the GET / documents page and POST scan route to `app`."""
    from fastapi.responses import HTMLResponse, RedirectResponse

    slug_by_id = {}
    for slug in AGENCIES:
        try:
            slug_by_id[repo.agency_id(slug)] = slug
        except ValueError:
            continue

    def _render(msg: Optional[str], is_err: bool) -> str:
        rows = repo.list_documents()
        counts = {"unscanned": 0, "scanned": 0, "failed": 0}
        for d in rows:
            counts[d.scan_status] = counts.get(d.scan_status, 0) + 1

        parts = [
            "<h1>Source documents</h1>",
            f"<p class='muted'>{counts['unscanned']} unscanned · "
            f"{counts['scanned']} scanned · {counts['failed']} failed</p>",
        ]
        if msg:
            cls = "note err" if is_err else "note"
            parts.append(f"<div class='{cls}'>{html.escape(msg)}</div>")
        if scanner is None:
            parts.append(
                "<div class='note err'>Scanning is unavailable — set SUPABASE_URL, "
                "SUPABASE_SERVICE_ROLE_KEY and ANTHROPIC_API_KEY in .env, then restart.</div>"
            )

        parts.append(
            "<table><tr><th>#</th><th>Agency</th><th>Year</th><th>Type</th>"
            "<th>By</th><th>Status</th><th></th></tr>"
        )
        for d in rows:
            agency = html.escape(slug_by_id.get(d.agency_id, f"agency#{d.agency_id}"))
            color = _STATUS_BADGE.get(d.scan_status, "#6b7280")
            status_cell = f"<span class='badge' style='background:{color}'>{d.scan_status}</span>"
            if d.scan_status == "scanned" and d.staged_count is not None:
                status_cell += f" <span class='muted'>{d.staged_count} staged</span>"
            elif d.scan_status == "failed" and d.last_error:
                status_cell += f" <span class='muted'>{html.escape(d.last_error[:80])}</span>"

            if scanner is not None and d.scan_status != "scanned":
                label = "Re-scan" if d.scan_status == "failed" else "Scan"
                action = (
                    f"<form method='post' action='/documents/{d.id}/scan' "
                    f"onsubmit=\"this.querySelector('button').textContent='Scanning…';"
                    f"this.querySelector('button').disabled=true;\">"
                    f"<button type='submit'>{label}</button></form>"
                )
            else:
                action = ""
            parts.append(
                f"<tr><td>{d.id}</td><td>{agency}</td><td>{d.year}</td>"
                f"<td>{html.escape(d.doc_type)}</td><td>[{html.escape(d.author_label)}]</td>"
                f"<td>{status_cell}</td><td>{action}</td></tr>"
            )
        parts.append("</table>")
        parts.append(
            "<p class='muted'>A scan stages extracted numbers into the review queue; "
            "nothing is published until you approve it.</p>"
        )
        return _page("".join(parts))

    @app.get("/", response_class=HTMLResponse)
    @app.get("/documents", response_class=HTMLResponse)
    def documents_page(msg: Optional[str] = None, err: int = 0):
        return _render(msg, bool(err))

    def _back(msg: str, *, err: bool) -> "RedirectResponse":
        # urlencode the message so an error string with %, &, or # can't produce
        # a malformed redirect URL. It's html.escape'd again on render.
        query = urlencode({"msg": msg, "err": "1"} if err else {"msg": msg})
        return RedirectResponse(f"/documents?{query}", status_code=303)

    @app.post("/documents/{document_id}/scan")
    def scan_route(document_id: int):
        # Sync def -> FastAPI runs it in a threadpool, so the long extract call
        # doesn't block the event loop.
        if scanner is None:
            return _back("Scanning is not configured", err=True)
        result = scanner(document_id)
        if result.get("ok"):
            return _back(
                f"Scanned doc #{document_id}: {result.get('staged_count', 0)} value(s) staged for review.",
                err=False,
            )
        return _back(
            f"Scan failed for doc #{document_id}: {result.get('error', 'unknown error')}", err=True
        )
