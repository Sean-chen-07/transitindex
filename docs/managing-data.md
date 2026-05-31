# Managing the data

A short, friendly guide to seeing what data we have, seeing what is missing, and
adding numbers by hand. No coding required — just two commands you copy-paste
into a terminal, and some typing in Excel.

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
