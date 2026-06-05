@echo off
REM One-click Hamilton HSR bulk load. Double-click in Windows Explorer, or run
REM from the repo root. Reads DATABASE_URL from .env.
REM Writes load_hamilton_result.json.
REM
REM Re-running is safe. Add --reset to wipe all Hamilton data first.
cd /d "%~dp0\ingest"
python -m transitindex_ingest hamilton-load ..\hamilton_hsr_live.csv --result ..\load_hamilton_result.json %*
echo.
pause
