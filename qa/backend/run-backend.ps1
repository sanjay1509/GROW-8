<##
Grow8 approved backend API tests (237 catalog IDs, 232 active + 5 deferred).
Does not edit application code or docker-compose.yml.
Usage from GROW-8 root:
  .\qa\backend\run-backend.ps1
  .\qa\backend\run-backend.ps1 -Suite smoke
  .\qa\backend\run-backend.ps1 -Suite sanity
  .\qa\backend\run-backend.ps1 -Suite regression
  .\qa\backend\run-backend.ps1 -CaseId CREATE-001
#>
param(
  [ValidateSet('all','smoke','sanity','regression')][string]$Suite = 'all',
  [string]$CaseId = ''
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$backend = Join-Path $root 'grow8-backend'
$tests = Join-Path $PSScriptRoot 'tests'
$reports = Join-Path $PSScriptRoot 'reports'
$init = Join-Path $backend 'db\init'

foreach ($path in @($backend, $tests, $init)) {
  if (-not (Test-Path $path)) { throw "Missing required folder: $path" }
}
if (-not (Test-Path (Join-Path $backend '.env'))) {
  throw 'Backend .env is missing. Create/configure grow8-backend/.env before testing.'
}
New-Item -ItemType Directory -Force -Path $reports | Out-Null

$pytest = 'python -m pytest tests/backend_qa --rootdir=/app/api -v -ra --tb=short '
$pytest += '--html=tests/reports/backend_report.html --self-contained-html '
$pytest += '--junitxml=tests/reports/backend_junit.xml'
if ($CaseId) {
  if ($CaseId -notmatch '^[A-Za-z0-9-]+$') { throw 'Invalid CaseId characters' }
  $pytest += " -k $CaseId"
} elseif ($Suite -ne 'all') {
  $pytest += " -m $Suite"
}

$cmd = "python -m pip install -q --disable-pip-version-check -r requirements-dev.txt pytest-html==4.1.1 && $pytest"
Write-Host "Starting Grow8 approved backend suite ($Suite)"
Write-Host 'Test DB: grow8_test (the application integration fixtures reset this database).'
Write-Host 'DO NOT run this against a shared or production MySQL instance.'
Push-Location $backend
try {
  # Ephemeral 'api' runner inherits its Docker Compose env and MySQL/RabbitMQ dependencies.
  # -u root installs testing dependencies only inside this temporary container.
  & docker compose run --rm -u root `
    -v "${tests}:/app/api/tests/backend_qa:ro" `
    -v "${init}:/app/db/init:ro" `
    -v "${reports}:/app/api/tests/reports" `
    api sh -c $cmd
  $exitCode = $LASTEXITCODE
} finally {
  Pop-Location
}
Write-Host "HTML report: $(Join-Path $reports 'backend_report.html')"
Write-Host "JUnit XML:   $(Join-Path $reports 'backend_junit.xml')"
if (Test-Path (Join-Path $reports 'backend_report.html')) {
  Write-Host 'Open report: Start-Process .\qa\backend\reports\backend_report.html'
}
exit $exitCode
