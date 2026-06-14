"""The human review page: a split-screen queue over core.pending_values.

Left pane: the pending values (ids resolved to agency slug / metric code / period
label with three batch lookups, not the per-row rebuild the JSON /pending endpoint
does). Right pane: a PDF viewer that jumps to the exact page a number came from, so
the reviewer can read the source report beside the number before deciding.

The Approve / Edit / Reject buttons call the EXISTING token-guarded JSON endpoints
(/pending/{id}/approve|reject, PATCH /pending/{id}) from the browser; the bearer
token is embedded in the page (safe because the server binds 127.0.0.1, the same
localhost trust boundary the open Scan endpoint already relies on). Approve is still
the only door into core.metric_values (Invariant #1).

GET /source/{sdid} streams the source PDF from Supabase Storage (in-memory cached
per document) so the viewer can render it inline; it needs the injected `storage`.
"""

from __future__ import annotations

import html
import json
from typing import Optional

from ..refdata import AGENCIES

_FLAG_FILTERS = ("all", "flagged", "clean")


def _fmt_value(value) -> str:
    try:
        return f"{value:,}"
    except (ValueError, TypeError):
        return str(value)


def mount_review(app, repo, *, token: Optional[str] = None, storage=None, db_lock=None) -> None:
    """Add GET /review (split-screen queue) and GET /source/{sdid} (PDF stream)."""
    import threading

    from fastapi import HTTPException
    from fastapi.responses import HTMLResponse, Response

    # Serialize DB access on the shared connection (see app.create_app).
    lock = db_lock or threading.Lock()
    _pdf_cache: dict[str, bytes] = {}  # storage_key -> bytes (one download per doc)

    def _slug_by_id() -> dict:
        out = {}
        for slug in AGENCIES:
            try:
                out[repo.agency_id(slug)] = slug
            except ValueError:
                continue
        return out

    @app.get("/source/{sdid}")
    def source_pdf(sdid: int):
        if storage is None or not hasattr(repo, "_conn"):
            raise HTTPException(status_code=503, detail="source viewing not configured")
        with lock:
            row = repo._conn.execute(
                "SELECT archive_uri FROM core.source_documents WHERE id = %s", (sdid,)
            ).fetchone()
        if not row or not row[0]:
            raise HTTPException(status_code=404, detail="no source file for this value")
        key = row[0]
        data = _pdf_cache.get(key)
        if data is None:
            try:
                data = storage.download(key)
            except Exception as exc:  # surface a clean 404 instead of a 500 stack
                raise HTTPException(status_code=404, detail=f"could not fetch {key}: {exc}")
            _pdf_cache[key] = data
        return Response(
            content=data,
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{html.escape(str(key))}"'},
        )

    @app.get("/review", response_class=HTMLResponse)
    def review_page(agency: Optional[str] = None, flag: str = "all"):
        if flag not in _FLAG_FILTERS:
            flag = "all"
        with lock:
            slug_by_id = _slug_by_id()
            code_by_id = {m.id: m.code for m in repo.list_metrics()}
            period_by_id = {p.id: p for p in repo.list_reporting_periods()}
            pending = repo.list_pending_values("pending")

        rows = []
        agencies_present = set()
        for p in pending:
            slug = slug_by_id.get(p.agency_id, f"agency#{p.agency_id}")
            agencies_present.add(slug)
            is_flagged = bool(p.flags)
            if flag == "flagged" and not is_flagged:
                continue
            if flag == "clean" and is_flagged:
                continue
            if agency and slug != agency:
                continue
            rows.append((p, slug, is_flagged))
        rows.sort(key=lambda r: (r[1], code_by_id.get(r[0].metric_id, ""), r[0].id))

        # --- filter bar ---
        def _flag_link(name: str) -> str:
            q = {"flag": name}
            if agency:
                q["agency"] = agency
            label = {"all": "All", "flagged": "Flagged only", "clean": "Clean only"}[name]
            cls = "chip on" if flag == name else "chip"
            qs = "&".join(f"{k}={v}" for k, v in q.items())
            return f"<a class='{cls}' href='/review?{qs}'>{label}</a>"

        agency_opts = ["<option value=''>All agencies</option>"]
        for slug in sorted(agencies_present):
            sel = " selected" if agency == slug else ""
            agency_opts.append(f"<option value='{html.escape(slug)}'{sel}>{html.escape(slug)}</option>")

        head = [
            "<div class='bar'>",
            "<a href='/' class='back'>&larr; documents</a>",
            f"<span id='count' class='count'>{len(rows)} to review</span>",
            "".join(_flag_link(n) for n in _FLAG_FILTERS),
            "<form method='get' style='display:inline'>",
            f"<input type='hidden' name='flag' value='{flag}'>",
            "<select name='agency' onchange='this.form.submit()'>", "".join(agency_opts), "</select>",
            "</form>",
            "</div>",
        ]

        # --- queue table ---
        body = [
            "<table><tr><th>Agency</th><th>Metric</th><th>Value</th><th>Period</th>"
            "<th>Conf</th><th>Flags</th><th>Source / decision</th></tr>"
        ]
        for p, slug, is_flagged in rows:
            code = code_by_id.get(p.metric_id, f"metric#{p.metric_id}")
            per = period_by_id.get(p.reporting_period_id)
            per_label = per.label if per else f"period#{p.reporting_period_id}"
            flags = ", ".join(p.flags) if p.flags else ""
            why = getattr(p, "reviewer_notes", None) or ""
            why_html = f"<div class='why'>{html.escape(why)}</div>" if why else ""
            conf = "" if p.confidence is None else f"{p.confidence}"
            sdid = "" if p.source_document_id is None else str(p.source_document_id)
            page = "" if p.page_number is None else str(p.page_number)
            view_label = f"View p.{page}" if page else "View"
            body.append(
                f"<tr id='row-{p.id}' data-id='{p.id}' data-sdid='{sdid}' data-page='{page or 1}'>"
                f"<td>{html.escape(slug)}</td>"
                f"<td>{html.escape(code)}</td>"
                f"<td class='num'>{_fmt_value(p.value)} <span class='unit'>{html.escape(p.unit or '')}</span></td>"
                f"<td>{html.escape(str(per_label))}</td>"
                f"<td>{conf}</td>"
                f"<td class='flags'>{html.escape(flags)}{why_html}</td>"
                f"<td class='actions'>"
                f"<button class='view' onclick='view(this)'>{view_label}</button>"
                f"<button class='ok' onclick='approve({p.id})'>Approve</button>"
                f"<button onclick='editval({p.id})'>Edit</button>"
                f"<button class='no' onclick='reject({p.id})'>Reject</button>"
                f"<span class='statuscell muted'></span>"
                f"</td>"
                f"</tr>"
            )
        body.append("</table>")
        if not rows:
            body.append("<p class='muted'>Nothing matches this filter.</p>")

        return _PAGE_TMPL.format(
            head="".join(head), body="".join(body), token=json.dumps(token or "")
        )


_PAGE_TMPL = """<!doctype html><html><head><meta charset='utf-8'>
<title>TransitIndex — review queue</title>
<style>
*{{box-sizing:border-box}}
body{{font:14px/1.5 system-ui,sans-serif;margin:0;padding:1rem 1.2rem;color:#1f2937}}
h1{{font-size:1.2rem;margin:.2rem 0 .4rem}}
.bar{{display:flex;gap:.5rem;align-items:center;flex-wrap:wrap;margin:.3rem 0 .8rem}}
.back{{color:#2563eb;text-decoration:none;font-weight:600}}
.count{{color:#6b7280;margin-right:.5rem}}
.chip{{font-size:.8rem;padding:.2rem .6rem;border-radius:.5rem;border:1px solid #d1d5db;color:#374151;text-decoration:none}}
.chip.on{{background:#2563eb;color:#fff;border-color:#2563eb}}
select{{font:inherit;padding:.2rem}}
.split{{display:flex;gap:1rem;align-items:flex-start}}
.left{{flex:1 1 52%;min-width:0;max-height:calc(100vh - 6rem);overflow:auto}}
.right{{flex:1 1 48%;position:sticky;top:.5rem;height:calc(100vh - 5rem);display:flex;flex-direction:column}}
.vlabel{{font-size:.9rem;padding:.4rem .2rem;font-weight:600}}
#pdf{{flex:1;width:100%;border:1px solid #d1d5db;border-radius:.4rem;background:#f9fafb}}
button{{font:inherit;padding:.2rem .5rem;border:1px solid #d1d5db;border-radius:.4rem;background:#f9fafb;cursor:pointer;margin-right:.2rem}}
button:hover{{background:#f3f4f6}}
button.view{{border-color:#2563eb;color:#1d4ed8}}
button.ok{{border-color:#16a34a;color:#15803d}}
button.no{{border-color:#dc2626;color:#b91c1c}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{text-align:left;padding:.3rem .45rem;border-bottom:1px solid #eee;vertical-align:middle}}
th{{font-size:.7rem;text-transform:uppercase;letter-spacing:.03em;color:#6b7280;position:sticky;top:0;background:#fff}}
.num{{font-variant-numeric:tabular-nums;font-weight:600;white-space:nowrap}}
.unit{{font-weight:400;color:#6b7280;font-size:.85em}}
.flags{{color:#b45309;font-size:.85em}}
.why{{color:#6b7280;font-size:.8em;font-style:italic;margin-top:.15rem;max-width:22rem}}
.muted{{color:#9ca3af}}
.actions{{white-space:nowrap}}
tr.sel td{{background:#eff6ff}}
.statuscell{{margin-left:.3rem;font-size:.85em}}
#toast{{position:fixed;top:.6rem;right:1rem;z-index:20;display:flex;flex-direction:column;gap:.35rem}}
.toast{{padding:.45rem .75rem;border-radius:.45rem;font-size:.88rem;box-shadow:0 2px 8px rgba(0,0,0,.18)}}
.toast.ok{{background:#ecfdf5;border:1px solid #86efac;color:#15803d}}
.toast.err{{background:#fef2f2;border:1px solid #fecaca;color:#b91c1c}}
</style></head><body>
<div id='toast'></div>
<h1>Review queue <span class='muted' style='font-size:.8rem;font-weight:400'>· read the source page on the right, then Approve / Edit / Reject. Nothing is public until you Approve.</span></h1>
{head}
<div class='split'>
  <div class='left'>{body}</div>
  <div class='right'>
    <div id='vlabel' class='vlabel muted'>Click &ldquo;View&rdquo; on any row to open its source report here, at the page the number came from. <a id='popout' target='_blank' rel='noopener' style='font-weight:400;font-size:.85em'></a></div>
    <iframe id='pdf' title='source report'></iframe>
  </div>
</div>
<script>
const TOKEN = {token};
const H = () => ({{'Authorization':'Bearer '+TOKEN,'Content-Type':'application/json'}});
function view(btn){{
  const tr = btn.closest('tr');
  const sdid = tr.dataset.sdid, page = tr.dataset.page || '1';
  if(!sdid){{ alert('No source report is linked to this value.'); return; }}
  const url = '/source/'+sdid+'#page='+page+'&zoom=page-width';
  document.getElementById('pdf').src = url;
  const c = tr.querySelectorAll('td');
  const lbl = document.getElementById('vlabel');
  lbl.firstChild.textContent =
    'Verifying: '+c[0].textContent+' · '+c[1].textContent+' = '+c[2].textContent+' ('+c[3].textContent+') — page '+page+' ';
  lbl.classList.remove('muted');
  const po = document.getElementById('popout'); po.href = url; po.textContent = '(open in new tab)';
  document.querySelectorAll('tr.sel').forEach(r=>r.classList.remove('sel'));
  tr.classList.add('sel');
}}
function toast(msg, ok){{
  const t=document.getElementById('toast');
  const d=document.createElement('div'); d.className='toast '+(ok?'ok':'err'); d.textContent=msg;
  t.appendChild(d); setTimeout(()=>d.remove(), ok?3000:7000);
}}
function removeRow(id){{
  const tr=document.getElementById('row-'+id); if(tr) tr.remove();
  const c=document.getElementById('count');
  if(c) c.textContent = document.querySelectorAll('tr[data-id]').length + ' to review';
}}
async function approve(id){{
  let r; try {{ r=await fetch('/pending/'+id+'/approve',{{method:'POST',headers:H()}}); }}
  catch(e){{ toast('Network error: '+e, false); return; }}
  if(r.ok){{ toast('Approved \\u2713 (now live)', true); removeRow(id); }}
  else {{ toast('Approve failed ('+r.status+'): '+(await r.text()), false); }}
}}
async function reject(id){{
  const reason=prompt('Reason for rejecting (optional):');
  let r; try {{ r=await fetch('/pending/'+id+'/reject',{{method:'POST',headers:H(),body:JSON.stringify({{reason:reason||null}})}}); }}
  catch(e){{ toast('Network error: '+e, false); return; }}
  if(r.ok){{ toast('Rejected \\u2717', true); removeRow(id); }}
  else {{ toast('Reject failed ('+r.status+')', false); }}
}}
async function editval(id){{
  const value=prompt('Corrected value (plain number, no commas):');
  if(value===null) return;
  let r; try {{ r=await fetch('/pending/'+id,{{method:'PATCH',headers:H(),body:JSON.stringify({{value:value}})}}); }}
  catch(e){{ toast('Network error: '+e, false); return; }}
  if(r.ok){{ toast('Edited \\u2192 '+value+' (saved for re-check)', true); removeRow(id); }}
  else {{ toast('Edit failed ('+r.status+')', false); }}
}}
</script>
</body></html>"""
