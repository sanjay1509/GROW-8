<##
Grow8 backend API suites:
  - regression: approved 237-case catalog (232 active + 5 deferred)
  - current-smoke: supplemental 68-case current API catalog
  - all: both catalogs
Does not edit application code or docker-compose.yml.
Usage from GROW-8 root:
  .\qa\backend\run-backend.ps1
  .\qa\backend\run-backend.ps1 -Suite regression
  .\qa\backend\run-backend.ps1 -Suite current-smoke
  .\qa\backend\run-backend.ps1 -Suite all
  .\qa\backend\run-backend.ps1 -Suite smoke
  .\qa\backend\run-backend.ps1 -Suite sanity
  .\qa\backend\run-backend.ps1 -CaseId CREATE-001
#>
param(
  [ValidateSet('all','smoke','sanity','regression','current-smoke')][string]$Suite = 'all',
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

$testFiles = switch ($Suite) {
  'regression' {
    @(
      'tests/backend_qa/test_01_health_auth_reference.py',
      'tests/backend_qa/test_02_opportunity_browse.py',
      'tests/backend_qa/test_03_opportunity_workflows.py',
      'tests/backend_qa/test_04_notifications.py'
    )
  }
  'current-smoke' {
    @(
      'tests/backend_qa/test_current_api_smoke.py',
      'tests/backend_qa/test_proposal_resume_api.py'
    )
  }
  default { @('tests/backend_qa') }
}

$reportPrefix = switch ($Suite) {
  'regression' { 'backend_regression' }
  'current-smoke' { 'backend_current-smoke' }
  default { 'backend' }
}

$pytest = 'python -m pytest ' + ($testFiles -join ' ')
$pytest += ' --rootdir=/app/api -v -ra --tb=short '
$pytest += "--html=tests/reports/${reportPrefix}_report.html --self-contained-html "
$pytest += "--junitxml=tests/reports/${reportPrefix}_junit.xml"
if ($CaseId) {
  if ($CaseId -notmatch '^[A-Za-z0-9-]+$') { throw 'Invalid CaseId characters' }
  $pytest += " -k $CaseId"
} elseif ($Suite -in @('smoke','sanity')) {
  $pytest += " -m $Suite"
}

$cmd = "python -m pip install -q --disable-pip-version-check -r requirements-dev.txt pytest-html==4.1.1 && $pytest"
Write-Host "Starting Grow8 backend API suite ($Suite)"
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
$htmlReport = Join-Path $reports "${reportPrefix}_report.html"
$junitReport = Join-Path $reports "${reportPrefix}_junit.xml"
Write-Host "HTML report: $htmlReport"
Write-Host "JUnit XML:   $junitReport"
if (Test-Path $htmlReport) {
  Write-Host "Open report: Start-Process $htmlReport"
}
exit $exitCode
