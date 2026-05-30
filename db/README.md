# `db/` — TransitIndex schema (Lane 0)

The database **contract**, owned by neither service. Built from
[../schema-design.md](../schema-design.md) §3–4 and
[../lane-0-foundation-spec.md](../lane-0-foundation-spec.md).

- **Two schemas:** `core` (ingestion-written, web reads only) and `app` (web-written).
  The read-only contract is enforced by a least-privilege `web_reader` role, not by convention.
- **Migrations:** plain SQL via [dbmate](https://github.com/amacneil/dbmate) — language-agnostic
  `up`/`down` files. No ORM owns the schema.
- **DB host:** Supabase (Postgres 15+; `NULLS NOT DISTINCT` requires 15+).

```
db/
  migrations/   001..007_*.sql   the schema contract (dbmate)
  seeds/        01..05_*.sql     reference data (modes, agencies, metrics, feeds) — NO metric values
  tests/        00..04_*.sql     plain-SQL assertions
  schema.sql                     generated snapshot (dbmate dump) — do not hand-edit
```

## 1. Install the tools (Windows)

No admin rights needed (this is the verified setup):

```powershell
# dbmate — single static exe. Download to a folder on PATH:
#   https://github.com/amacneil/dbmate/releases/latest/download/dbmate-windows-amd64.exe
# psql + pg_dump — the PostgreSQL client. Easiest no-admin route is Scoop:
irm get.scoop.sh | iex       # install Scoop (user-scope)
scoop install postgresql     # provides psql + pg_dump
dbmate --version
psql --version
pg_dump --version
```

## 2. Point at your database

Copy `../.env.example` to `../.env` and paste your Supabase connection string:

- Supabase Dashboard → **Connect** → **Session pooler** (port **5432**, IPv4-friendly).
  Do **not** use the Transaction pooler (6543).
- Append `?sslmode=require`.

```
DATABASE_URL=postgresql://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require
```

dbmate reads `DATABASE_URL` automatically (it loads `.env`).

## 3. Run migrations

```powershell
dbmate --no-dump-schema up     # apply 001..007
dbmate --no-dump-schema down   # revert the last migration (repeatable; full round-trip = down x7 then up)

# Refresh db/schema.sql. We DON'T use `dbmate dump` here: its dump covers the whole
# database, and a Supabase project has ~10 built-in schemas (auth, storage, ...) that
# would bury our contract. So we scope pg_dump to just our two schemas:
pg_dump $env:DATABASE_URL --schema-only --no-owner --schema=core --schema=app -f db/schema.sql
```

> `--no-dump-schema` skips dbmate's built-in auto-dump (same whole-DB reason); regenerate
> `db/schema.sql` with the scoped `pg_dump` above instead.

## 4. Load seeds (reference data only — no metric values)

```powershell
Get-ChildItem db/seeds/*.sql | Sort-Object Name | ForEach-Object {
  psql $env:DATABASE_URL -v ON_ERROR_STOP=1 -f $_.FullName
}
```
Seeds are re-runnable (`ON CONFLICT DO NOTHING`).

## 5. Run tests

Each test raises an exception on failure, so `ON_ERROR_STOP=1` makes a failure exit non-zero.
A passing run prints one `PASS <name>` per file.

```powershell
Get-ChildItem db/tests/*.sql | Sort-Object Name | ForEach-Object {
  psql $env:DATABASE_URL -v ON_ERROR_STOP=1 -f $_.FullName
}
```

| Test | Proves (acceptance #) |
|---|---|
| `00_seed_assertions` | counts 10/10/20, `primary_modes` ↔ `agency_modes`, derived↔formula (#2, #3, #8) |
| `01_constraints`     | CHECK rejects bad enum; FK rejects orphan (#4) |
| `02_invariants`      | `one_current_value` blocks a 2nd current row, incl. NULL mode (#5) |
| `03_trigger`         | audit row written on value UPDATE, correct old/new (#6) |
| `04_grants`          | `web_reader` SELECT-only on `core`, write on `app` (#7) |

`01`–`03` create throwaway fixtures inside a transaction and `ROLLBACK`, so they leave no trace;
run them **after** seeds (they reference seeded metrics).
