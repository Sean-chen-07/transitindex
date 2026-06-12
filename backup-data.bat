@echo off
REM One-click database backup. Double-click in Windows Explorer, or run from the
REM repo root. Dumps the irreplaceable DATA (core + app schemas: reviewed values,
REM provenance, accounts) to backups\transitindex-data-YYYYMMDD-HHMM.sql.
REM Run this after every data-entry session and before any --reset.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\backup-data.ps1"
echo.
pause
