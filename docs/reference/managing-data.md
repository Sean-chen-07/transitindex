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

Open it in Excel. Along the bottom you'll see these tabs:

1. **How to use** — the same plain instructions, right inside the file.
2. **Data Dictionary** — what every number means: a plain-language description,
   its unit, whether you **type** it ("Sourced") or it's **worked out for you**
   ("Calculated"), the formula for the calculated ones, and how often it's
   normally reported.
3. **One tab per agency** — TTC, STM, TransLink, and so on. These are where you
   type — each agency has its own tab.

### What an agency tab looks like

An agency tab is a grid. **Down the left** is one row per number we track
(ridership, operating revenue, service hours, costs, and so on). **Across the
top**, the columns run left to right by year, and each year is split into the
twelve months, the four quarters, a year-to-date total, and the full-year total:

```
Jan Feb Mar  Q1  |  Apr May Jun  Q2  |  Jul Aug Sep  Q3  |  Oct Nov Dec  Q4  |  YTD  |  Year
```

At the bottom of every agency tab is a small **Fleet** section: one row per
vehicle type (Bus, Subway, Light rail, Commuter rail, Streetcar). For rail,
count **trains**, not individual cars.

### The colour code

The two colours mean the same thing everywhere:

- **White cells** — type here.
- **Grey cells** — worked out automatically (the quarter, year-to-date and
  full-year totals, and the ratios). **Don't type in them** —
  anything you put there is ignored and recalculated.

## Step 2 — Add data

Open your agency's tab (for example **TTC**) — everything for that agency goes on
that one tab. Open the **Data Dictionary** tab any time you're unsure what a
number means.

- **Ridership and Operating revenue** — type each **month** you have, in the
  white month cells. The quarter, year-to-date and full-year totals fill in for
  you.
- **Every other yearly number** (service hours, costs, fleet age, the
  balance-sheet lines, and so on) — type it **once**, in that row's **Year**
  column. The month and quarter cells on those rows are greyed out — you don't
  use them.
- **Fleet** — in the Fleet section at the bottom, type the number of vehicles for
  each mode (Bus, Subway, Light rail, Commuter rail, Streetcar) in the **Year**
  column. For rail, count **trains**, not individual cars.
- **Calculated rows** (ratios like farebox recovery and cost per rider, and net
  debt) show a grey formula in the **Year** column — they fill themselves in once
  their inputs are present. You never type them.

Type real numbers straight from your source (an annual report, a budget, an
open-data file). Leave anything you don't have **blank** — never guess.

**About the year columns.** The year across the top is just the calendar year —
**2024** means calendar-year 2024 for most agencies. **Metrolinx** and **BC
Transit** run their financial year to the end of March; for them, the column
labelled **2024** means their 2024–25 financial year. There's nothing to set —
just type each agency's figures under the matching year.

## Step 3 — Save it back

When you're done editing, save the Excel file, then run:

```
python -m transitindex_ingest import-xlsx transitindex-data.xlsx
```

This reads your white cells, saves them into the database, **rolls the months up
into quarter and yearly totals**, works out the calculated metrics (ratios, net
debt), and refreshes the rankings. You'll see a short summary of how
many values were saved.

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
file was wrong and you want to wipe it and reload from scratch — add **`--reset`**.
It deletes **only that source's own numbers** (the ones this loader itself
published): anything you typed into the workbook by hand, or approved from a PDF,
for the same agencies is left alone. You only need this for a forced full reload;
normal updates never do. Because double-clicking can't pass options, run it from a
terminal.

As a safety step, `--reset` won't delete anything on its own: it first **prints
exactly what it would remove, agency by agency**, and then stops. To actually go
ahead, add **`--yes`**:

```
load-statcan.bat --reset            # shows what would be deleted, deletes nothing
load-statcan.bat --reset --yes      # actually deletes this source's rows, then reloads
```

Tip: run [`backup-data.bat`](../../backup-data.bat) before any `--reset --yes`, so
you always have a copy to restore from.

Need the rest of the pipeline (PDFs, rankings, the review queue)? Every command is
listed in [reference-ingest-cli.md](reference-ingest-cli.md).
