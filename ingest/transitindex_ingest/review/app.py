"""FastAPI app for the human review queue.

`create_app(repo)` builds the app over an injected Repository (tests pass an
InMemoryRepository). fastapi is imported lazily inside the factory so importing
this module never requires fastapi.

Approval is the ONLY path that moves a value into core.metric_values, and it
goes through promotion.promote_one -- nothing here writes metric_values
directly (Invariant #1: an unreviewed value never reaches metric_values).
"""

from __future__ import annotations

import secrets
from decimal import Decimal, InvalidOperation
from typing import Optional

from ..db.models import PendingValue
from ..db.repository import Repository
from ..promotion import promote_one
from ..refdata import AGENCIES


def _slug_by_agency_id(repo: Repository) -> dict[int, str]:
    """agency_id -> slug, via the public id-resolver over seeded slugs."""
    return {repo.agency_id(slug): slug for slug in AGENCIES}


def _code_by_metric_id(repo: Repository) -> dict[int, str]:
    """metric_id -> code, via list_metrics()."""
    return {m.id: m.code for m in repo.list_metrics()}


def _summary(repo: Repository, p: PendingValue) -> dict:
    """The list-row shape: identifiers resolved to slugs/codes, value as str."""
    return {
        "id": p.id,
        "agency_slug": _slug_by_agency_id(repo).get(p.agency_id),
        "metric_code": _code_by_metric_id(repo).get(p.metric_id),
        "reporting_period_id": p.reporting_period_id,
        "value": str(p.value),
        "unit": p.unit,
        "flags": list(p.flags),
        "confidence": None if p.confidence is None else str(p.confidence),
        "review_status": p.review_status,
    }


def _detail(repo: Repository, p: PendingValue) -> dict:
    """The full detail shape for one pending row."""
    row = _summary(repo, p)
    row.update(
        {
            "mode_id": p.mode_id,
            "service_scope": p.service_scope,
            "currency": p.currency,
            "quality": p.quality,
            "comparable_flag": p.comparable_flag,
            "crosscheck_value": (
                None if p.crosscheck_value is None else str(p.crosscheck_value)
            ),
            "source_document_id": p.source_document_id,
            "page_number": p.page_number,
            "table_reference": p.table_reference,
            "extraction_method": p.extraction_method,
            "reviewer_notes": p.reviewer_notes,
        }
    )
    return row


def create_app(repo: Repository, *, token: Optional[str] = None):
    """Build the FastAPI review app over `repo`.

    Mutating endpoints (approve/reject/edit) require an
    ``Authorization: Bearer <token>`` header matching `token` -- they are the
    only door into live metric_values (Invariant #1), so they are never open.
    Read endpoints stay open. When `token` is None every mutating request is
    rejected (fail closed); the CLI refuses to serve without a configured token.
    """
    from fastapi import Body, Depends, FastAPI, Header, HTTPException

    app = FastAPI(title="TransitIndex review queue")

    def require_token(authorization: Optional[str] = Header(default=None)) -> None:
        """Reject a mutating request lacking a valid bearer token."""
        provided = ""
        if authorization and authorization.startswith("Bearer "):
            provided = authorization[len("Bearer ") :]
        if not token or not secrets.compare_digest(provided, token):
            raise HTTPException(status_code=401, detail="invalid or missing API token")

    def _require_pending(pending_id: int) -> PendingValue:
        p = repo.get_pending_value(pending_id)
        if p is None:
            raise HTTPException(status_code=404, detail=f"unknown pending id: {pending_id}")
        return p

    @app.get("/pending")
    def list_pending(status: Optional[str] = "pending") -> list[dict]:
        return [_summary(repo, p) for p in repo.list_pending_values(status)]

    @app.get("/pending/{pending_id}")
    def get_pending(pending_id: int) -> dict:
        return _detail(repo, _require_pending(pending_id))

    @app.post("/pending/{pending_id}/approve", dependencies=[Depends(require_token)])
    def approve(pending_id: int) -> dict:
        _require_pending(pending_id)
        repo.update_pending(pending_id, review_status="approved")
        metric_value_id = promote_one(repo, pending_id)
        return {"pending_id": pending_id, "metric_value_id": metric_value_id}

    @app.post("/pending/{pending_id}/reject", dependencies=[Depends(require_token)])
    def reject(pending_id: int, reason: Optional[str] = Body(default=None, embed=True)) -> dict:
        _require_pending(pending_id)
        repo.update_pending(pending_id, review_status="rejected", reviewer_notes=reason)
        return _detail(repo, _require_pending(pending_id))

    @app.patch("/pending/{pending_id}", dependencies=[Depends(require_token)])
    def edit(
        pending_id: int,
        value: Optional[str] = Body(default=None, embed=True),
        reviewer_notes: Optional[str] = Body(default=None, embed=True),
    ) -> dict:
        _require_pending(pending_id)
        new_value: Optional[Decimal] = None
        if value is not None:
            try:
                new_value = Decimal(value)
            except (InvalidOperation, ValueError):
                raise HTTPException(status_code=422, detail=f"invalid value: {value!r}")
        repo.update_pending(
            pending_id,
            value=new_value,
            review_status="needs_edit",
            reviewer_notes=reviewer_notes,
        )
        return _detail(repo, _require_pending(pending_id))

    return app
