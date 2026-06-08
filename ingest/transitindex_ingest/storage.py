"""Supabase Storage client -- the cloud home for raw source PDFs.

Talks to the Storage REST API directly over httpx (already a dependency); no
Supabase SDK. The service-role key is a master credential, so this only ever
runs server-side (the ingest/review process), never in the web app.

httpx is imported lazily so importing this module never requires it; only the
methods that actually hit the network do.

Endpoints used (base = {SUPABASE_URL}/storage/v1):
  - create bucket : POST   {base}/bucket
  - upload/upsert : POST   {base}/object/{bucket}/{key}   (header x-upsert: true)
  - download      : GET    {base}/object/{bucket}/{key}
  - object info   : GET    {base}/object/info/{bucket}/{key}
"""

from __future__ import annotations

import hashlib
from typing import Optional

DEFAULT_BUCKET = "annual-reports"
_TIMEOUT = 120  # PDFs are up to ~16 MB; allow a generous upload/download window.


def sha256_hex(data: bytes) -> str:
    """Hex sha256 of the given bytes -- the catalog's file_hash."""
    return hashlib.sha256(data).hexdigest()


class SupabaseStorage:
    """Minimal create/upload/download/exists over the Supabase Storage REST API."""

    def __init__(self, url: str, service_role_key: str, bucket: str = DEFAULT_BUCKET) -> None:
        import httpx  # lazy: importing this module must not require httpx

        self._bucket = bucket
        self._base = f"{url.rstrip('/')}/storage/v1"
        # Supabase's gateway wants the key in BOTH headers for service-role calls.
        self._client = httpx.Client(
            timeout=_TIMEOUT,
            headers={
                "Authorization": f"Bearer {service_role_key}",
                "apikey": service_role_key,
            },
        )

    @classmethod
    def from_config(cls, cfg, bucket: str = DEFAULT_BUCKET) -> "SupabaseStorage":
        """Build from a Config; raise a clear error if the keys are unset."""
        if not cfg.supabase_url or not cfg.supabase_service_role_key:
            raise RuntimeError(
                "Supabase Storage needs SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY "
                "in .env (Project Settings -> API -> Project URL + service_role key)."
            )
        return cls(cfg.supabase_url, cfg.supabase_service_role_key, bucket)

    @property
    def bucket(self) -> str:
        return self._bucket

    def ensure_bucket(self, *, public: bool = False) -> None:
        """Create the bucket if it does not already exist (idempotent)."""
        resp = self._client.post(
            f"{self._base}/bucket",
            json={"id": self._bucket, "name": self._bucket, "public": public},
        )
        if resp.status_code in (200, 201):
            return
        # Already exists -> the API returns 400/409 with a "Duplicate"/"already exists"
        # message. Treat that as success; re-raise anything else.
        body = resp.text.lower()
        if resp.status_code in (400, 409) and ("exist" in body or "duplicate" in body):
            return
        resp.raise_for_status()

    def upload(self, key: str, data: bytes, *, content_type: str = "application/pdf") -> None:
        """Upload (overwriting if present) `data` to `key` within the bucket."""
        resp = self._client.post(
            f"{self._base}/object/{self._bucket}/{key}",
            content=data,
            headers={"Content-Type": content_type, "x-upsert": "true"},
        )
        resp.raise_for_status()

    def download(self, key: str) -> bytes:
        """Fetch the object bytes at `key` (raises on a missing object)."""
        resp = self._client.get(f"{self._base}/object/{self._bucket}/{key}")
        resp.raise_for_status()
        return resp.content

    def exists(self, key: str) -> bool:
        """True if an object exists at `key`."""
        resp = self._client.get(f"{self._base}/object/info/{self._bucket}/{key}")
        if resp.status_code == 200:
            return True
        if resp.status_code == 404:
            return False
        resp.raise_for_status()
        return False

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SupabaseStorage":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
