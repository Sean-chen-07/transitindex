@echo off
REM One-click StatCan bulk load. Double-click in Windows Explorer, or run from
REM the repo root. Reads DATABASE_URL from .env. Writes load_statcan_result.json.
REM
REM Re-running is safe (diff-aware: only changed months are superseded).
REM Add "--reset --yes" to wipe this feed's OWN StatCan rows first (forced full
REM reload; hand-entered + PDF values are kept). "--reset" alone only previews.
cd /d "%~dp0\ingest"
python -m transitindex_ingest statcan-load ..\statcan_23100307.csv --result ..\load_statcan_result.json %*
echo.
pause
