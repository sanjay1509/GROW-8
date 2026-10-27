# Run as: .\qa\show-docker-report.ps1 -Layer frontend -Suite smoke
# Open http://localhost:9323 while this PowerShell session is serving the report.
param(
    [ValidateSet('frontend', 'backend', 'database')]
    [string]$Layer = 'frontend',
    [ValidateSet('smoke', 'sanity', 'regression')]
    [string]$Suite = 'smoke'
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$latest = Join-Path $repoRoot "qa/reports/$Layer/$Suite/latest.json"
if (-not (Test-Path $latest)) {
    throw "No $Layer $Suite report exists. Run that suite first."
}
$meta = Get-Content $latest -Raw | ConvertFrom-Json
$reportPath = '/workspace/qa/' + ($meta.report -replace '\\', '/')
$backend = Join-Path $repoRoot 'grow8-backend'
$composeArgs = @('-f','docker-compose.yml','-f','docker-compose.override.yml','-f','docker-compose.qa.yml')
Push-Location $backend
try {
    Write-Host "Serving $Layer $Suite report on http://localhost:9323 (Ctrl+C to stop)"
    docker compose @composeArgs run --rm --no-deps -p 9323:9323 qa-frontend npx playwright show-report $reportPath --host 0.0.0.0 --port 9323
}
finally {
    Pop-Location
}
