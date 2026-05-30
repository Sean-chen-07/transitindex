# ingest/ — TransitIndex ingestion

The Python pipeline that **writes** the `core.*` schema in Postgres. Per the
project's decoupling invariant, ingestion writes and the web app only reads —
this package never assumes Node/web and never reads back through the app.

Everything here is **offline-testable**: the core logic imports only the Python
standard library, and the real-I/O adapters (psycopg, anthropic, pdfplumber,
fastapi) import their dependencies lazily, so the test suite runs green with no
database, no API keys, and no network.

## Package layout

```
transitindex_ingest/
  contract.py     MetricValueRecord (frozen) + SourceRef + the Literal enums.
                  The canonical value shape every component codes against.
  config.py       load_config() -> DATABASE_URL / ANTHROPIC_API_KEY (may be None).
  refdata.py      Seed mirror: AGENCIES, METRICS, MODES, SOURCE_FEEDS,
                  STATCAN_AGENCY_MAP. Keeps in sync with db/seeds/*.
  periods.py      monthly_period() / annual_period() -> (type, start, end, label).
  db/
    models.py     Read-model dataclasses the repo returns.
    repository.py Repository (typing.Protocol) — the abstract write/read API.
    memory.py     InMemoryRepository — the offline workhorse for all tests.
    postgres.py   PostgresRepository — real backend via psycopg (lazy import).
tests/            Pure-stdlib + pytest. conftest.py has the shared fixtures.
```

## Running the tests

```
cd ingest
python -m pytest -q
```

pytest is the only thing you need installed. `pyproject.toml` sets
`pythonpath = ["."]`, so `import transitindex_ingest` works with **no install
step**. If pytest is missing: `python -m pip install pytest`.

## Wiring a real database / LLM later

1. Copy the repo-root `.env.example` to `.env` and set `DATABASE_URL` (and
   `ANTHROPIC_API_KEY` if using LLM extraction). `config.load_config()` reads it
   (via python-dotenv if installed, else a stdlib parser).
2. `pip install -r requirements.txt` to pull the optional real-I/O deps.
3. Construct `PostgresRepository(config.database_url)` instead of
   `InMemoryRepository()`. Both satisfy the same `Repository` protocol, so
   pipeline code is unchanged.

The schema this package targets lives in `db/schema.sql`; the seed data it
mirrors lives in `db/seeds/`.
