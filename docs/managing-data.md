# Managing the data

A short, friendly guide to seeing what data we have, seeing what is missing, and
adding numbers by hand. No coding required — just two commands you copy-paste
into a terminal, and some typing in Excel.

> **The one rule to remember:** leave a cell **blank** if you don't have the
> number — never type a guess. The website shows the last known number for you,
> so a blank here is always fine.

## Before you start (one time)

All the numbers live in a database (Supabase). The pipeline knows how to reach
it through a setting called `DATABASE_URL`, which lives in a file named `.env`
at the top of the project. If that file is already set up, you don't need to
touch it.

**Right now the database has no real numbers in it yet — that is normal.**
Nothing has been collected from the transit agencies so far. The steps below are
how the first numbers get in.

> If `DATABASE_URL` is *not* set, the commands still run, but they only do a
> practice run in memory and save nothing. You'll see a note saying so. To save
> for real, make sure `.env` has `DATABASE_URL` filled in.

You run the two commands below from a terminal opened in the `ingest` folder.
Every command starts with the same prefix: `python -m transitindex_ingest`.

## Step 1 — Get the spreadsheet

Run this to pull whatever is currently in the database into an Excel file:

```
python -m transitindex_ingest export-xlsx
```

This creates a file called **`transitindex-data.xlsx`** in the `ingest` folder.
(Because the database is empty today, the spreadsheet comes out blank and ready
to fill — that's expected.)

Open it in Excel. It has six tabs along the bottom:

1. **How to use** — the same plain instructions, right inside the file.
2. **Data Dictionary** — what every number means, its unit, and — handily — a
   **Sheet** column telling you which tab to type it on.
3. **Monthly** — month-by-month ridership and fare revenue.
4. **Annual Fundamentals** — the once-a-year operating numbers (service hours,
   costs, fleet, and so on), one row per agency per year.
5. **Balance Sheet** — the agency's once-a-year financial position (assets,
   liabilities), from the audited financial statements.
6. **Gaps** — a quick count, for each row, of how many numbers are filled in
   versus still missing. Use this to see what's left to do.

### The colour code

The same three colours mean the same thing on every tab:

- **White cells** — type here.
- **Grey cells** — worked out automatically (yearly totals, ratios, accounting
  checks). **Don't type in them** — anything you put there is ignored and
  recalculated.
- **Light-yellow cells** — optional, only needed for the rare quarterly case. A
  blank light-yellow cell is perfectly normal.

## Step 2 — Add data

Open the **Data Dictionary** tab if you're not sure where a number goes — its
**Sheet** column points you to the right tab. Otherwise:

- **Monthly tab** — for ridership and fare revenue. Type each month you have;
  the **yearly total is worked out for you** when you import. If a city only
  publishes a yearly number, skip this tab and use Annual Fundamentals instead.
- **Annual Fundamentals tab** — the once-a-year operating numbers. Ridership and
  fare revenue show up here too, but as a **grey yearly total** — you don't
  re-type them, they come from the Monthly tab.
- **Balance Sheet tab** — the eight financial-position lines from the audited
  statements. **Net Debt** and the two **Check** columns are grey: they're
  worked out for you so you can eyeball that the numbers add up.

Type real numbers straight from your source (an annual report, a budget, an
open-data file). Leave anything you don't have **blank** — never guess.

**About the Period column** (on Annual Fundamentals and Balance Sheet). Each row
already has its Period filled in for you:

- **2024** means the calendar year 2024 (most agencies).
- **FY2024-25** means a financial year ending in spring 2025 — for **Metrolinx**
  and **BC Transit**, whose year ends in March.
- **2024-Q1** means the first quarter of 2024. Only **TransLink** reports its
  balance sheet this often; you'd type this one in yourself for that rare case.

## Step 3 — Save it back

When you're done editing, save the Excel file, then run:

```
python -m transitindex_ingest import-xlsx transitindex-data.xlsx
```

This reads your white cells, saves them into the database, **adds up the months
into yearly totals**, works out the calculated metrics (ratios, net debt), and
refreshes the rankings. You'll see a short summary of how many values were saved.

To confirm the round-trip worked, run the export again and reopen the file —
your numbers (and the grey calculated cells) should now be there:

```
python -m transitindex_ingest export-xlsx
```

## Good to know

- **The grey cells are worked out for you** on both sides — in Excel as you
  type, and again on the server when you import. You never need to type them in,
  and you shouldn't.
- **Blanks stay blank.** The spreadsheet never fills in a guessed or carried-
  forward number, and import skips every blank cell. Showing a stale-but-real
  number to visitors is the website's job, not the spreadsheet's.
- **Fixing a number is safe.** If you typed something wrong, just correct the
  white cell and import again. The new value cleanly supersedes the old one —
  you don't need to delete anything first.
- **Want to know exactly what a column means?** See
  [docs/data-dictionary.md](data-dictionary.md) (the same definitions also live
  on the Data Dictionary tab inside the spreadsheet).

## Bulk-load a whole agency at once

Two of our sources publish their numbers as open data you can download in a
single file — so for these, you never type anything. Skip the spreadsheet and
use a **one-click loader** instead:

- **StatCan** — Statistics Canada's monthly ridership table (23-10-0307), which
  covers about a dozen of the biggest agencies in one file.
- **Hamilton** — Hamilton HSR's monthly ridership, published as open data.

For everything else — the annual numbers you read off an agency's annual report
or budget — use the spreadsheet (Steps 1–3 above) and enter them by hand.

### Running a loader

1. Download the source file and save it at the top of the project, with the name
   the loader expects:
   - StatCan → **`statcan_23100307.csv`**
   - Hamilton → **`hamilton_hsr_live.csv`**
2. Double-click the matching loader (or run it from the project's top folder):
   - **`load-statcan.bat`**
   - **`load-hamilton.bat`**

A window opens, the loader runs, and it prints a short summary — how many numbers
it added and how many it updated — then waits so you can read it. It also saves
that summary to a file (`load_statcan_result.json` or `load_hamilton_result.json`)
you can keep or ignore. It reads `DATABASE_URL` from the same `.env` as everything
else; if that isn't set, it does a harmless practice run and saves nothing.

**Re-running is safe.** A loader only changes the months that actually changed
since last time and leaves the rest alone, so you can run it again whenever a new
month is published — no mess, no duplicates.

**Starting a source over.** If you need a clean slate for one source — say the
file was wrong and you want to wipe it and reload from scratch — add **`--reset`**,
which deletes that source's numbers first and then loads the file fresh. You only
need this for a forced full reload; normal updates never do. Because double-
clicking can't pass options, run it from a terminal for this:

```
load-statcan.bat --reset
```

Need the rest of the pipeline (PDFs, rankings, the review queue)? Every command is
listed in [reference-ingest-cli.md](reference-ingest-cli.md).
