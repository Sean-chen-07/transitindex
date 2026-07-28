# NTD snapshot CSVs

Committed snapshots of the two FTA National Transit Database Socrata datasets,
downloaded by `python ingest/scripts/fetch_ntd.py --out db/seeds/ntd/`:

- `ntd_monthly.csv` — Complete Monthly Ridership (`8bui-9xvu`), Full Reporters only.
- `ntd_annual.csv`  — NTD Annual Data, Metrics (`ekg5-frzt`).

They are the input to `python ingest/scripts/generate_ntd_agencies.py`, which
emits `db/seeds/08_agencies_us.sql` and `ingest/transitindex_ingest/refdata_us.py`,
and they are also what the `ntd-monthly` / `ntd-annual` CLI loaders ingest.

Snapshots downloaded + committed 2026-07-28 (monthly since 2019-01, Full
Reporters; annual all rows). Re-run fetch + generator + loaders to refresh.
