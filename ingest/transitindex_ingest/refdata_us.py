"""US agency reference data — GENERATED, do not hand-edit.

Produced by `python ingest/scripts/generate_ntd_agencies.py` from downloaded
snapshots of the FTA National Transit Database (data.transportation.gov):
  * Complete Monthly Ridership (Socrata 8bui-9xvu) — reporter type + modes
  * NTD Annual Data, Metrics (Socrata ekg5-frzt) — names, city, state

The generator also emits the matching SQL seed (db/seeds/08_agencies_us.sql).
Both files are committed; re-running the generator preserves the existing slug
of every ntd_id it has seen before (slugs are permanent URLs).

This file starts EMPTY: data.transportation.gov was unreachable from the
environment that built the integration (egress-policy blocked), so the first
real generation must be run from a machine with normal network access:

    python ingest/scripts/fetch_ntd.py --out db/seeds/ntd/
    python ingest/scripts/generate_ntd_agencies.py

Until then the NTD adapters map zero agencies (every row lands in `.skipped`)
and no US agency exists in the seeds — the pipeline is wired but idle.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

# slug -> {subdivision (2-letter state), fiscal_year_end_month, currency, country,
#          ntd_id, primary_modes}. Same shape as refdata.AGENCIES plus
#          country/currency/ntd_id (the Canadian dict carries those implicitly).
US_AGENCIES: Mapping[str, Mapping] = MappingProxyType({})

# NTD ID (5-digit zero-padded string, e.g. "00001") -> agency slug.
NTD_AGENCY_MAP: Mapping[str, str] = MappingProxyType({})
