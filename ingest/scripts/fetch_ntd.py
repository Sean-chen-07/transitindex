"""Download NTD snapshot CSVs from data.transportation.gov (Socrata SODA API).

Run from the repo root, from a machine with normal outbound network access
(the API needs no authentication; an app token only lifts throttling):

    python ingest/scripts/fetch_ntd.py --out db/seeds/ntd/

Writes two CSVs with API field names as headers (what the adapters and the
seed generator consume):

  * ntd_monthly.csv — Complete Monthly Ridership (Socrata 8bui-9xvu),
    Full Reporters only, months >= --since (default 2019-01).
  * ntd_annual.csv  — NTD Annual Data, Metrics (Socrata ekg5-frzt), all rows.
  * ntd_agency_info.csv — NTD Reporter Agency Information (Socrata ccvf-fykn),
    all rows; supplies each reporter's fiscal-year end date.

Optional env: NTD_APP_TOKEN — sent as X-App-Token to avoid 429 throttling.
Retries each page up to 4 times with exponential backoff. Stdlib only.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://data.transportation.gov/resource"
PAGE_SIZE = 50_000

DATASETS = {
    "ntd_monthly.csv": {
        "id": "8bui-9xvu",
        # Server-side filter keeps the download to what we ingest.
        "where": "reporter_type='Full Reporter' AND date>='{since}-01T00:00:00'",
        "order": "ntd_id,mode,tos,date",
    },
    "ntd_annual.csv": {
        "id": "ekg5-frzt",
        "where": None,
        "order": "ntd_id,report_year,mode,type_of_service",
    },
    # Reporter Agency Information: the only NTD table carrying each reporter's
    # fiscal-year end (fy_end_date), which the seed generator turns into
    # fiscal_year_end_month. Small (~3k rows).
    "ntd_agency_info.csv": {
        "id": "ccvf-fykn",
        "where": None,
        "order": "ntd_id",
    },
}


def fetch_page(dataset_id: str, where: str | None, order: str, offset: int) -> str:
    params = {"$limit": PAGE_SIZE, "$offset": offset, "$order": order}
    if where:
        params["$where"] = where
    url = f"{BASE}/{dataset_id}.csv?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url)
    token = os.environ.get("NTD_APP_TOKEN")
    if token:
        request.add_header("X-App-Token", token)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                return response.read().decode("utf-8")
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == 4:
                raise
            delay = 2 ** (attempt + 1)
            print(f"  retry in {delay}s ({exc})", file=sys.stderr)
            time.sleep(delay)
    raise AssertionError("unreachable")


def download(name: str, spec: dict, out_dir: Path, since: str) -> None:
    where = spec["where"].format(since=since) if spec["where"] else None
    out_path = out_dir / name
    offset = 0
    pages = 0
    with out_path.open("w", encoding="utf-8", newline="") as out:
        while True:
            page = fetch_page(spec["id"], where, spec["order"], offset)
            lines = page.splitlines(keepends=True)
            if not lines:
                break
            body = lines if pages == 0 else lines[1:]  # keep only the first header
            data_rows = len(lines) - 1
            if data_rows <= 0:
                break
            out.writelines(body)
            pages += 1
            offset += PAGE_SIZE
            print(f"  {name}: {offset if data_rows == PAGE_SIZE else offset - PAGE_SIZE + data_rows} rows...")
            if data_rows < PAGE_SIZE:
                break
    print(f"wrote {out_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="db/seeds/ntd/", help="Output directory.")
    parser.add_argument(
        "--since", default="2019-01", help="Monthly cutoff YYYY-MM (default 2019-01)."
    )
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, spec in DATASETS.items():
        print(f"downloading {spec['id']} -> {name}")
        download(name, spec, out_dir, args.since)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
