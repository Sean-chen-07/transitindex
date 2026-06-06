# Managing the data

A short, friendly guide to seeing what data we have, seeing what is missing, and
adding numbers by hand. No coding required — just two commands you copy-paste
into a terminal, and some typing in Excel.

> **Heads-up (2026-05-31):** the workbook is being expanded to show a lot more —
> a **Monthly** tab for ridership/revenue, a **Balance Sheet** tab for the
> agencies' financial position, and a **Period** column so a row can be a month,
> a quarter, or a year. The guide below still describes the **current** workbook
> (one annual grid). It will be updated when the new tabs ship. The plan and the
> new colour/blank rules are in
> [balance-sheet-and-frequency-plan.md](../balance-sheet-and-frequency-plan.md) —
> the one rule to remember: **leave a cell blank if you don't have the number;
> the website carries the last known value forward for you, so you never type a
> guess.**

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

Open it in Excel. It has four tabs along the bottom:

1. **How to use** — the same plain instructions, right inside the file.
2. **Data Dictionary** — what every column means, its unit, and (for the
   calculated columns) the formula behind it.
3. **Data** — the grid you actually edit: one row per agency per year.
4. **Gaps** — a quick count, for each row, of how many of the 14 numbers are
   filled in versus still missing. Use this to see what's left to do.

## Step 2 — Add data

Go to the **Data** tab. Each row is one agency for one year. Find the row you
want and type real numbers in, taken straight from your source (an annual
report, a budget document, and so on).

- **White columns** are the ones you fill in — there are 14 of them (ridership,
  operating expenses, fleet size, and so on).
- **Grey columns** are calculated automatically (revenue per rider, farebox
  recovery ratio, cost per rider, and the other ratios). They fill themselves in
  by formula as you type the white columns. **Don't type in the grey columns** —
  anything you put there gets ignored and recalculated.
- Leave a cell **blank** if you don't have that number yet. Never guess. A blank
  grey cell just means one of its inputs is still missing.

**About the Year column.** The Year is the calendar year the reporting year
*begins*. For most agencies that's just the calendar year (Year 2024 = the year
2024). For **Metrolinx** and **BC Transit**, whose financial year ends in March,
Year 2024 means their **2024–25 fiscal year**.

## Step 3 — Save it back

When you're done editing, save the Excel file, then run:

```
python -m transitindex_ingest import-xlsx transitindex-data.xlsx
```

This reads your numbers, saves them into the database, automatically works out
the 6 calculated metrics, and refreshes the rankings. You'll see a short summary
of how many values were saved.

To confirm the round-trip worked, run the export again and reopen the file —
your numbers (and the calculated columns) should now be there:

```
python -m transitindex_ingest export-xlsx
```

## Good to know

- **The grey/calculated columns are worked out for you** on both sides — in
  Excel as you type, and again on the server when you import. You never need to
  type them in, and you shouldn't.
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
