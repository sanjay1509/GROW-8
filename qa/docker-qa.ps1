# Run as: .\qa\docker-qa.ps1 -Layer frontend -Suite smoke
# It builds the Playwright QA container and then runs only the selected layer(s).
param(
    [ValidateSet('frontend', 'backend', 'database', 'all')]
    [string]$Layer = 'frontend',
    [ValidateSet('smoke', 'sanity', 'regression')]
    [string]$Suite = 'smoke'
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $repoRoot 'grow8-backend'
if (-not (Test-Path (Join-Path $backend '.env'))) {
    throw 'Missing grow8-backend/.env. Create it from .env.example, then retry.'
}
New-Item -ItemType Directory -Force -Path (Join-Path $PSScriptRoot 'reports') | Out-Null
$composeArgs = @('-f','docker-compose.yml','-f','docker-compose.override.yml','-f','docker-compose.qa.yml')
Push-Location $backend
try {
    Write-Host 'Building the Playwright test runner Docker image...'
    docker compose @composeArgs build qa-frontend
    if ($LASTEXITCODE -ne 0) { throw 'Docker QA image build failed.' }
    $layers = if ($Layer -eq 'all') { @('frontend','backend','database') } else { @($Layer) }
    $failed = $false
    foreach ($currentLayer in $layers) {
        Write-Host "`nRunning $currentLayer - $Suite in Docker..."
        docker compose @composeArgs run --rm "qa-$currentLayer" npm run "test:${currentLayer}:${Suite}"
        if ($LASTEXITCODE -ne 0) { $failed = $true }
        $latest = Join-Path $repoRoot "qa/reports/$currentLayer/$Suite/latest.json"
        if (Test-Path $latest) {
            $meta = Get-Content $latest -Raw | ConvertFrom-Json
            Write-Host "HTML report saved under: qa/$($meta.report)/index.html"
        }
    }
    if ($failed) { throw 'One or more test suites failed. Check HTML reports.' }
}
finally {
    Pop-Location
}
