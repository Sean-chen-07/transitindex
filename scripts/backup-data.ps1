# Backs up the data that cannot be re-fetched from public sources: human-reviewed
# values, the audit/provenance chain (core schema) and user accounts/subscriptions
# (app schema). The schema itself is rebuildable from db\migrations, so this dump is
# --data-only. Reads DATABASE_URL from the repo-root .env (same file the loaders use).
#
# Run via backup-data.bat (double-click) or:  powershell -File scripts\backup-data.ps1

$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "ERROR: $envFile not found. Copy .env.example to .env first." -ForegroundColor Red
    exit 1
}

$dbUrl = $null
foreach ($line in Get-Content $envFile) {
    if ($line -match '^\s*DATABASE_URL\s*=\s*(.+)\s*$') { $dbUrl = $Matches[1].Trim('"').Trim("'") }
}
if (-not $dbUrl) {
    Write-Host "ERROR: DATABASE_URL not found in .env" -ForegroundColor Red
    exit 1
}

$backupDir = Join-Path $root "backups"
New-Item -ItemType Directory -Force $backupDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmm"
$out = Join-Path $backupDir "transitindex-data-$stamp.sql"

Write-Host "Dumping core + app data to $out ..."
pg_dump $dbUrl --data-only --no-owner --schema=core --schema=app -f $out
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: pg_dump failed (is it on PATH? see db\README.md section 1)." -ForegroundColor Red
    exit 1
}

$size = [math]::Round((Get-Item $out).Length / 1KB)
Write-Host "Done: $out ($size KB)." -ForegroundColor Green
Write-Host "Keep a copy OUTSIDE this laptop (cloud drive / USB) — Supabase free tier has no automatic backups."
